from django.conf.urls import url
from raster_aggregation.views import AggregationView

urlpatterns = [
    # Url to request aggregate results
    url(r'^aggregate/(?P<area>[0-9]+)/$',
        AggregationView.as_view(),
        name='aggregate'),
]
