from __future__ import unicode_literals

from rest_framework import routers

from django.conf.urls import include, url
from raster_aggregation.views import ValueCountResultViewSet

router = routers.DefaultRouter()

router.register(r'valuecountresult', ValueCountResultViewSet, base_name='valuecountresult')

urlpatterns = [

    url(r'api/', include(router.urls)),

]
