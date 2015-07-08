from django.conf.urls import url
from raster_aggregation.views import AggregationView

# from rest_framework import routers
# from raster_aggregation.views import AggregationAreaExportViewSet, AggregationAreaGeoViewSet

# router = routers.router()

# router.register(r'aggregationarea', AggregationAreaGeoViewSet,
#     base_name='aggregationarea')

# router.register(r'aggregationareaexport', AggregationAreaExportViewSet,
#     base_name='aggregationareaexport')


urlpatterns = [
    # Url to request aggregate results
    url(r'^aggregate/(?P<area>[0-9]+)/$',
        AggregationView.as_view(),
        name='aggregate'),
]
