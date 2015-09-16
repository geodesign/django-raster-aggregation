import traceback

from celery import shared_task

from raster.models import RasterLayer

from .models import ValueCountResult


@shared_task()
def compute_value_count(obj, layer_id, compute_area=True):
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
            ValueCountResult.objects.create(
                aggregationarea=area,
                formula=formula,
                layer_names=ids,
                zoom=zoom,
                units='acres' if compute_area else ''
            )
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
