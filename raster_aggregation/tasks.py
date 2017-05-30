from __future__ import unicode_literals

import os
import shutil
import tempfile
import traceback
import zipfile

from celery import task
from raster.models import RasterLayer

from django.contrib.gis.gdal import CoordTransform, DataSource, SpatialReference
from raster_aggregation.models import AggregationLayer, ValueCountResult
from raster_aggregation.utils import WEB_MERCATOR_SRID, convert_to_multipolygon


@task()
def aggregation_layer_parser(agglayer_id):
    """
    This function pushes the shapefile data from the AggregationLayer
    into the AggregationArea table.
    """
    # Get aggregation layer.
    agglayer = AggregationLayer.objects.get(id=agglayer_id)

    # Clean previous parse log
    agglayer.log('Started parsing Aggregation Layer {0}'.format(agglayer.id))

    tmpdir = tempfile.mkdtemp()

    shapefilename = os.path.basename(agglayer.shapefile.name)

    shapefilepath = os.path.join(tmpdir, shapefilename)

    # Get zipped shapefile from storage
    try:
        # Access shapefile and store locally
        shapefile = open(shapefilepath, 'wb')
        for chunk in agglayer.shapefile.chunks():
            shapefile.write(chunk)
        shapefile.close()
    except:
        shutil.rmtree(tmpdir)
        agglayer.log('Error: Could not download file, aborted parsing')
        return

    # Open and extract zipfile
    try:
        zf = zipfile.ZipFile(shapefilepath)
        zf.extractall(tmpdir)
    except:
        shutil.rmtree(tmpdir)
        agglayer.log('Error: Could not open zipfile, aborted parsing')
        return

    # Remove zipfile
    os.remove(shapefilepath)

    # Set shapefile as datasource for GDAL and get layer
    try:
        ds = DataSource(tmpdir)
        lyr = ds[0]
    except:
        shutil.rmtree(tmpdir)
        agglayer.log('Error: Failed to extract layer from shapefile, aborted parsing')
        return

    # Check if name column exists
    if agglayer.name_column.lower() not in [field.lower() for field in lyr.fields]:
        agglayer.log(
            'Error: Name column "{0}" not found, aborted parsing. '
            'Available columns: {1}'.format(agglayer.name_column, lyr.fields)
        )
        return

    # Setup transformation to default ref system
    try:
        ct = CoordTransform(lyr.srs, SpatialReference(WEB_MERCATOR_SRID))
    except:
        shutil.rmtree(tmpdir)
        agglayer.log('Error: Layer srs not specified, aborted parsing')
        return

    # Remove existing patches before re-creating them
    agglayer.aggregationarea_set.all().delete()

    # Loop through features
    for feat in lyr:
        # Get geometry and transform to WGS84
        try:
            wgsgeom = feat.geom
            wgsgeom.transform(ct)
        except:
            agglayer.log('Warning: Failed to transform feature fid {0}\n'.format(feat.fid))
            continue

        try:
            # Ignore z-dim
            wgsgeom.coord_dim = 2

            # Assure that feature is a valid multipolygon
            geom = convert_to_multipolygon(wgsgeom.geos)
        except:
            agglayer.log(
                'Warning: Failed to convert feature fid {0} to'
                ' multipolygon\n'.format(feat.fid)
            )
            continue

        # Add warning if geom is not valid
        if geom.valid_reason != 'Valid Geometry':
            agglayer.log(
                'Warning: Found invalid geometry for'
                ' feature fid {0}\n'.format(feat.fid)
            )
            continue

        # If geom is empty, conversion was not successful, issue
        # warning and continue
        if geom.empty:
            agglayer.log(
                'Warning: Failed to convert feature fid'
                ' {0} to valid geometry\n'.format(feat.fid)
            )
            continue

        # Create aggregation area
        try:
            agglayer.aggregationarea_set.create(
                name=feat.get(agglayer.name_column),
                aggregationlayer=agglayer,
                geom=geom
            )
        except:
            agglayer.log(
                'Warning: Failed to create AggregationArea '
                'for feature fid {0}\n'.format(feat.fid)
            )

    agglayer.log('Finished parsing Aggregation Layer {0}'.format(agglayer.id))

    # Remove tempdir with unzipped shapefile
    shutil.rmtree(tmpdir)


def compute_value_count_for_aggregation_layer(obj, layer_id, compute_area=True, grouping='auto'):
    """
    Precomputes value counts for a given aggregation area and a rasterlayer.
    """
    rast = RasterLayer.objects.get(id=layer_id)

    if rast.datatype not in ['ca', 'ma']:
        obj.log(
            'ERROR: Rasterlayer {0} is not categorical. '
            'Can only compute value counts on categorical layers'
        )
        return

    # Prepare parameters data for aggregator
    ids = {'a': str(rast.id)}
    formula = 'a'
    zoom = rast._max_zoom

    # Open parse log
    obj.log(
        'Starting Value count for AggregationLayer {agg} on RasterLayer {rst} on original Geometries'
        .format(agg=obj.id, rst=rast.id)
    )

    for area in obj.aggregationarea_set.all():
        # Remove existing results
        area.valuecountresult_set.filter(rasterlayers=rast, formula=formula, layer_names=ids).delete()

        obj.log('Computing Value Count for area {0} and raster {1}'.format(area.id, rast.id))

        try:
            # Store result, this automatically creates value on save
            result, created = ValueCountResult.objects.get_or_create(
                aggregationarea=area,
                formula=formula,
                layer_names=ids,
                zoom=zoom,
                units='acres' if compute_area else '',
                grouping=grouping
            )
            compute_single_value_count_result(result.id)
        except:
            obj.log(
                'ERROR: Failed to compute value count for '
                'area {0} and raster {1}'.format(area.id, rast.id)
            )
            obj.log(traceback.format_exc())

    obj.log(
        'Ended Value count for AggregationLayer {agg} '
        'on RasterLayer {rst}'.format(agg=obj.id, rst=rast.id)
    )


@task()
def compute_single_value_count_result(valuecount_id):
    """
    Computes value counts for a given input set.
    """
    vc = ValueCountResult.objects.get(id=valuecount_id)
    # If this object was newly created, populate its value count asynchronously.
    if vc.status not in (ValueCountResult.COMPUTING, ValueCountResult.FINISHED):
        vc.populate()


@task()
def compute_batch_value_count_results(aggregationlayer, formula, layer_names, zoom, units, grouping='auto'):
    """
    Precomputes value counts for a given input set.
    """
    # Compute zoom if not provided
    if zoom is None:
        # Get layer ids
        ids = layer_names.split(',')

        # Parse layer ids into dictionary with variable names
        ids = {idx.split('=')[0]: idx.split('=')[1] for idx in ids}

        # Compute zoom level
        zoom = min(
            RasterLayer.objects.filter(id__in=ids.values())
            .values_list('metadata__max_zoom', flat=True)
        )

    for area in aggregationlayer.aggregationarea_set.all():
        result, created = ValueCountResult.objects.get_or_create(
            aggregationarea=area,
            formula=formula,
            layer_names=ids,
            zoom=zoom,
            units=units,
            grouping=grouping
        )
        compute_single_value_count_result(result.id)
