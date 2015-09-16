from rest_framework import routers

from django.conf.urls import include, url

from .views import AggregationAreaValueViewSet

router = routers.DefaultRouter()

router.register(r'aggregationareavalue', AggregationAreaValueViewSet, base_name='aggregationareavalue')

urlpatterns = [

    url(r'api/', include(router.urls)),

]
