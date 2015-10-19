import traceback

from celery import shared_task

from raster.models import RasterLayer

from .models import ValueCountResult


@shared_task()
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
            ValueCountResult.objects.get_or_create(
                aggregationarea=area,
                formula=formula,
                layer_names=ids,
                zoom=zoom,
                units='acres' if compute_area else '',
                grouping=grouping
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


@shared_task()
def compute_single_value_count_result(area, formula, layer_names, zoom, units, grouping='auto'):
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

    ValueCountResult.objects.get_or_create(
        aggregationarea=area,
        formula=formula,
        layer_names=ids,
        zoom=zoom,
        units=units,
        grouping=grouping
    )


@shared_task()
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
        ValueCountResult.objects.get_or_create(
            aggregationarea=area,
            formula=formula,
            layer_names=ids,
            zoom=zoom,
            units=units,
            grouping=grouping
        )
