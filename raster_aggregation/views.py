"""Set of views for the aggregation app"""

from rest_framework import filters, viewsets
from rest_framework.settings import api_settings
from rest_framework_csv import renderers
from rest_framework_gis.filters import InBBOXFilter

from .models import AggregationArea
from .serializers import AggregationAreaExportSerializer, AggregationAreaGeoSerializer


class AggregationAreaGeoViewSet(viewsets.ModelViewSet):
    """
    API endpoint that returns Aggregation Area geometries in GeoJSON format.
    """
    serializer_class = AggregationAreaGeoSerializer
    allowed_methods = ('GET', )
    filter_backends = (InBBOXFilter, filters.DjangoFilterBackend, )
    filter_fields = ('name', 'aggregationlayer', )
    bbox_filter_field = 'geom'
    paginate_by = None
    bbox_filter_include_overlapping = True

    def get_queryset(self):
        queryset = AggregationArea.objects.all()
        zoom = self.request.QUERY_PARAMS.get('zoom', None)
        if zoom:
            queryset = queryset.filter(aggregationlayer__min_zoom_level__lte=zoom, aggregationlayer__max_zoom_level__gte=zoom)
        return queryset


class AggregationAreaExportViewSet(viewsets.ModelViewSet):
    """
    API endpoint that returns Aggregation Area geometries in GeoJSON format.
    """
    queryset = AggregationArea.objects.all()
    serializer_class = AggregationAreaExportSerializer
    allowed_methods = ('GET', )
    filter_fields = ('name', 'aggregationlayer', )
    paginate_by = None
    renderer_classes = [renderers.CSVRenderer] + api_settings.DEFAULT_RENDERER_CLASSES
