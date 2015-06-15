from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.db import connection


def convert_to_multipolygon(geom):
    """
    Function to convert a geometry into a MultiPolygon. This function will
    return an empty geometry if conversion is not possible. Examples are
    if the geometry are points or lines, then an empty geomtetry is returned.
    """
    cursor = connection.cursor()

    # Check if geom is empty
    if geom.empty:
        return MultiPolygon([], srid=4326)
    # Check if geom has no area (point & line)
    if geom.area == 0:
        return MultiPolygon([], srid=4326)

    # Try to iteratively convert to valid multi polygon
    for i in range(10):
        # Check if conditions are met
        if geom.geom_type != 'MultiPolygon' or geom.valid_reason != 'Valid Geometry':
            # Run cleaning sequence
            try:
                sql = "SELECT ST_AsText(ST_CollectionExtract(ST_MakeValid('{wkt}'), 3))".format(wkt=geom.wkt)
                cursor.execute(sql)
                geom = GEOSGeometry(cursor.fetchone()[0])
                if geom.geom_type != 'MultiPolygon':
                    geom = MultiPolygon(geom, srid=4326)
            # If cleaning sequence raises exception, return empty geometry
            except:
                return MultiPolygon([], srid=4326)
        # If conditions are met, stop iterating
        else:
            break

    # Check if all conditions are statisfied after conversion
    if geom.empty or geom.area == 0 or geom.geom_type != 'MultiPolygon'\
            or geom.valid_reason != 'Valid Geometry':
        return MultiPolygon([], srid=4326)
    else:
        return geom


def remove_sliver_polygons(geom, srid=3086, minarea_sqm=10):
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
        geom.transform(4326)

    # Make sure its a proper multi polygon
    geom = convert_to_multipolygon(geom)

    # Return cleaned geometry
    return geom


def distance_in_radians(point, distance, srid=3086):
    """Returns a distance from a point given meters in radians units"""

    point_clone = point.transform(srid, clone=True)
    point_clone.x += distance
    point_clone.transform(4326)

    return point.distance(point_clone)
