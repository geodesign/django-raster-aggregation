import json

from rest_framework import filters, viewsets
from rest_framework.exceptions import APIException
from rest_framework.settings import api_settings
from rest_framework_csv import renderers
from rest_framework_gis.filters import InBBOXFilter

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View
from raster.formulas import RasterAlgebraParser
from raster.models import RasterLayer
from raster.valuecount import aggregator

from .models import AggregationArea, AggregationLayer
from .serializers import (
    AggregationAreaExportSerializer, AggregationAreaGeoSerializer, AggregationAreaSerializer,
    AggregationAreaValueSerializer
)

from rest_framework_extensions.cache.decorators import (
    cache_response
)


class MissingQueryParameter(APIException):
    status_code = 500
    default_detail = 'Missing Query Parameter.'


class AggregationView(View):

    def __init__(self, *args, **kwargs):
        super(AggregationView, self).__init__(*args, **kwargs)
        self.parser = RasterAlgebraParser()

    def get(self, request, *args, **kwargs):
        """
        Return value count for this aggregation area and an algebra expression.

        Should currently only be used with categorical rasters, as it will look
        for unique values.
        """
        # Look for required query parameters
        if 'zoom' not in request.GET:
            raise MissingQueryParameter(detail='Missing query parameter: zoom')
        elif 'formula' not in request.GET:
            raise MissingQueryParameter(detail='Missing query parameter: formula')
        elif 'layers' not in request.GET:
            raise MissingQueryParameter(detail='Missing query parameter: layers')

        # Get aggregation area
        area_id = self.kwargs.get('area')
        area = get_object_or_404(AggregationArea, id=area_id)

        # Compute tilerange for this area and the given zoom level
        zoom = int(request.GET.get('zoom'))

        # Get layer ids
        ids = request.GET.get('layers').split(',')

        # Parse layer ids into dictionary with variable names
        ids = {idx.split('=')[0]: idx.split('=')[1] for idx in ids}

        # Get formula from request
        formula = request.GET.get('formula')

        # Compute aggregate results using aggregator
        results = aggregator(ids, zoom, area.geom, formula)

        # Prepare data for json response
        results = json.dumps(results)

        return HttpResponse(results, content_type='application/json')


class AggregationAreaViewSet(viewsets.ModelViewSet):
    """
    Regular aggregation Area model view endpoint.
    """
    serializer_class = AggregationAreaSerializer
    allowed_methods = ('GET', )
    filter_fields = ('aggregationlayer', )

    def get_queryset(self):
        qs = AggregationArea.objects.all()
        ids = self.request.query_params.get('ids')
        if ids:
            ids = ids.split(',')
            return qs.filter(id__in=ids)
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
    filter_fields = ('aggregationlayer', )

    def initial(self, request, *args, **kwargs):
        """
        Look for required request query parameters.
        """
        if 'zoom' not in request.GET:
            raise MissingQueryParameter(detail='Missing query parameter: zoom')
        elif 'formula' not in request.GET:
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

    @cache_response(key_func='calculate_cache_key')
    def list(self, request, *args, **kwargs):
        """
        List method wrapped with caching decorator.
        Use the default timeout which is cache forever.
        """
        return super(AggregationAreaValueViewSet, self).list(request, *args, **kwargs)

    def calculate_cache_key(self, view_instance, view_method, request, *args, **kwargs):
        """
        Creates the cache key based on query parameters and change dates from
        related objects.
        """
        # Add request parameters to cache key
        cache_key_data = [
            request.GET.get('formula', ''),
            request.GET.get('layers', ''),
            request.GET.get('zoom', ''),
            str('True' == request.GET.get('acres', ''))
        ]

        # Add aggregationlayer id and modification date
        agglayer_id = request.GET.get('aggregationlayer', '')
        if agglayer_id:
            modified = AggregationLayer.objects.get(id=agglayer_id).modified
            modified = str(modified).replace(' ', '-')
            cache_key_data.append('-'.join(['agg', agglayer_id, modified]))

        # Construct layer ids array to get modification dates
        ids = [idx.split('=')[1] for idx in request.GET.get('layers').split(',')]

        # Get raster layer array
        layers = RasterLayer.objects.filter(id__in=ids).values_list('id', 'modified')

        # Add layer modification time stamps to cache key
        for layer in layers:
            cache_key_data.append('-'.join(['lyr', str(layer[0]), str(layer[1]).replace(' ', '-')]))

        return '|'.join(cache_key_data)


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
