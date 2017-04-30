from rest_framework import filters, viewsets
from rest_framework.exceptions import APIException
from rest_framework_extensions.cache.decorators import cache_response
from rest_framework_gis.filters import InBBOXFilter

from .models import AggregationArea, AggregationLayer
from .serializers import (
    AggregationAreaGeoSerializer, AggregationAreaSimplifiedSerializer, AggregationAreaValueSerializer,
    AggregationLayerSerializer
)


class MissingQueryParameter(APIException):
    status_code = 500
    default_detail = 'Missing Query Parameter.'


class AggregationAreaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Regular aggregation Area model view endpoint.
    """
    serializer_class = AggregationAreaSimplifiedSerializer
    filter_backends = (filters.DjangoFilterBackend, )
    filter_fields = ('aggregationlayer', )

    def get_queryset(self):
        qs = AggregationArea.objects.all()
        ids = self.request.query_params.get('ids')
        if ids:
            qs = qs.filter(id__in=ids.split(','))
        return qs

    @cache_response(key_func='calculate_cache_key')
    def list(self, request, *args, **kwargs):
        """
        List method wrapped with caching decorator.
        """
        return super(AggregationAreaViewSet, self).list(request, *args, **kwargs)

    def calculate_cache_key(self, view_instance, view_method, request, *args, **kwargs):
        """
        Creates the cache key based on query parameters and change dates from
        related objects.
        """
        # Add ids to cache key data
        cache_key_data = [
            request.GET.get('ids', '')
        ]

        # Add aggregationlayer id and modification date
        agglayer_id = request.GET.get('aggregationlayer', '')
        if agglayer_id:
            modified = AggregationLayer.objects.get(id=agglayer_id).modified
            modified = str(modified).replace(' ', '-')
            cache_key_data.append('-'.join(['agg', agglayer_id, modified]))

        return '|'.join(cache_key_data)


class AggregationAreaValueViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Regular aggregation Area model view endpoint.
    """
    serializer_class = AggregationAreaValueSerializer
    filter_backends = (filters.DjangoFilterBackend, )
    filter_fields = ('aggregationlayer', )

    def initial(self, request, *args, **kwargs):
        """
        Look for required request query parameters.
        """
        if 'formula' not in request.GET:
            raise MissingQueryParameter(detail='Missing query parameter: formula')
        elif 'layers' not in request.GET:
            raise MissingQueryParameter(detail='Missing query parameter: layers')

        return super(AggregationAreaValueViewSet, self).initial(request, *args, **kwargs)

    def get_queryset(self):
        qs = AggregationArea.objects.all()
        ids = self.request.query_params.get('ids')
        if ids:
            ids = ids.split(',')
            return qs.filter(id__in=ids)
        return qs


class AggregationAreaGeoViewSet(viewsets.ReadOnlyModelViewSet):
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


class AggregationLayerViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = AggregationLayerSerializer

    def get_queryset(self):
        return AggregationLayer.objects.all()
