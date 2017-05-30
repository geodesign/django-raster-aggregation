from __future__ import unicode_literals

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.db import connection

WEB_MERCATOR_SRID = 3857


def convert_to_multipolygon(geom):
    """
    Function to convert a geometry into a MultiPolygon. This function will
    return an empty geometry if conversion is not possible. Examples are
    if the geometry are points or lines, then an empty geomtetry is returned.
    """
    cursor = connection.cursor()

    # Store this geom's srid
    srid = geom.srid

    # Setup empty response
    empty = MultiPolygon([], srid=srid)

    # Check if geom is empty or has no area (point & line)
    if geom.empty or geom.area == 0:
        return empty

    # Try to iteratively convert to valid multi polygon
    for i in range(10):
        # Check if conditions are met
        if geom.geom_type != 'MultiPolygon' or geom.valid_reason != 'Valid Geometry':
            # Run cleaning sequence
            try:
                sql = "SELECT ST_AsText(ST_CollectionExtract(ST_MakeValid('{wkt}'), 3))".format(wkt=geom.wkt)
                cursor.execute(sql)
                geom = GEOSGeometry(cursor.fetchone()[0], srid=srid)
                if geom.geom_type != 'MultiPolygon':
                    geom = MultiPolygon(geom, srid=srid)
            # If cleaning sequence raises exception, return empty geometry
            except:
                return empty
        # If conditions are met, stop iterating
        else:
            break

    # Check if all conditions are statisfied after conversion
    if geom.empty or geom.area == 0 or geom.geom_type != 'MultiPolygon'\
            or geom.valid_reason != 'Valid Geometry':
        return empty
    else:
        return geom


def remove_sliver_polygons(geom, srid=WEB_MERCATOR_SRID, minarea_sqm=10):
    """Routine to remove sliver polygons from a multipolygon object"""

    # Transform to projected coordinate system
    clean_geom = geom.transform(srid, clone=True)

    # Split into components
    components = []
    while clean_geom:
        components.append(clean_geom.pop())

    # Filter components by size
    big_components = [x for x in components if x.area > minarea_sqm]

    # If small area was found, update geom with larger components
    if(len(big_components) < len(components)):
        geom = MultiPolygon(big_components, srid=srid)
        geom.transform(WEB_MERCATOR_SRID)

    # Make sure its a proper multi polygon
    geom = convert_to_multipolygon(geom)

    # Return cleaned geometry
    return geom


def distance_in_radians(point, distance, srid=WEB_MERCATOR_SRID):
    """Returns a distance from a point given meters in radians units"""

    point_clone = point.transform(srid, clone=True)
    point_clone.x += distance
    point_clone.transform(WEB_MERCATOR_SRID)

    return point.distance(point_clone)
