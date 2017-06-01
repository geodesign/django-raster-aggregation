from __future__ import unicode_literals

from rest_framework import routers

from django.conf.urls import include, url
from raster_aggregation.views import AggregationAreaViewSet, ValueCountResultViewSet, VectorTilesView

router = routers.DefaultRouter()

router.register(r'valuecountresult', ValueCountResultViewSet)
router.register(r'aggregationarea', AggregationAreaViewSet)

urlpatterns = [

    url(r'api/', include(router.urls)),

    # Vector tiles endpoint.
    url(
        r'^vtiles/(?P<layergroup>[^/]+)/(?P<z>[0-9]+)/(?P<x>[0-9]+)/(?P<y>[0-9]+)(?P<response_format>\.json|\.pbf)$',
        VectorTilesView.as_view(),
        name='vector_tiles'
    ),

]
