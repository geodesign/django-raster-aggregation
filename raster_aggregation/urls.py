from __future__ import unicode_literals

from rest_framework import routers

from django.conf.urls import include, url
from raster_aggregation.views import (
    AggregationAreaViewSet, AggregationLayerVectorTilesViewSet, AggregationLayerViewSet, ValueCountResultViewSet
)

router = routers.DefaultRouter()

router.register(r'valuecountresult', ValueCountResultViewSet)
router.register(r'aggregationarea', AggregationAreaViewSet)
router.register(r'aggregationlayer', AggregationLayerViewSet)
router.register(
    r'vtiles/(?P<aggregationlayer>[^/]+)/(?P<z>[0-9]+)/(?P<x>[0-9]+)/(?P<y>[0-9]+).(?P<frmt>json|pbf)',
    AggregationLayerVectorTilesViewSet,
    base_name='vectortiles'
)

urlpatterns = [
    url(r'api/', include(router.urls)),
]
