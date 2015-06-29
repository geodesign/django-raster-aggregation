from raster_aggregation.views import AggregationAreaExportViewSet, AggregationAreaGeoViewSet
from rest_framework import routers

router = routers.router()

router.register(r'aggregationarea', AggregationAreaGeoViewSet,
    base_name='aggregationarea')

router.register(r'aggregationareaexport', AggregationAreaExportViewSet,
    base_name='aggregationareaexport')
