from __future__ import unicode_literals

from raster.models import RasterLayer
from rest_framework import filters, viewsets
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework_gis.filters import InBBOXFilter

from django.db import IntegrityError
from raster_aggregation.exceptions import DuplicateError
from raster_aggregation.models import AggregationArea, AggregationLayer, ValueCountResult
from raster_aggregation.serializers import (
    AggregationAreaGeoSerializer, AggregationAreaSimplifiedSerializer, AggregationLayerSerializer,
    ValueCountResultSerializer
)
from raster_aggregation.tasks import compute_single_value_count_result


class AggregationLayerViewSet(viewsets.ModelViewSet):

    queryset = AggregationLayer.objects.all()
    serializer_class = AggregationLayerSerializer


class AggregationAreaViewSet(viewsets.ModelViewSet):
    """
    Regular aggregation Area model view endpoint.
    """
    queryset = AggregationArea.objects.all()
    serializer_class = AggregationAreaSimplifiedSerializer
    filter_backends = (filters.DjangoFilterBackend, )
    filter_fields = ('aggregationlayer', )


class ValueCountResultViewSet(RetrieveModelMixin,
                              ListModelMixin,
                              CreateModelMixin,
                              DestroyModelMixin,
                              viewsets.GenericViewSet):
    """
    Regular aggregation Area model view endpoint.
    """
    queryset = ValueCountResult.objects.all()
    serializer_class = ValueCountResultSerializer
    filter_backends = (filters.DjangoFilterBackend, )
    filter_fields = ('aggregationarea__aggregationlayer', )

    def perform_create(self, serializer):
        # Get list of rasterlayers based on layer names dict.
        rasterlayers = [RasterLayer.objects.get(id=pk) for pk in serializer.validated_data.get('layer_names').values()]

        # Get zoom level, the serializer has a default to trick the validation. The
        # unique constraints on the model disable the required=False argument.
        if serializer.validated_data.get('zoom') != -1:
            zoom = serializer.validated_data.get('zoom')
        else:
            # Compute zoom if not provided. Work at the resolution of the
            # input layer with the highest zoom level by default, or the
            # lowest one if requested.
            zlevels = [rst.metadata.max_zoom for rst in rasterlayers]
            if 'minmaxzoom' in self.request.GET:
                # Get the minimum of maxzoom levels
                zoom = min(zlevels)
            elif 'maxzoom' in self.request.GET:
                # Limit maximum zoom level
                maxzoom = int(self.request.GET.get('maxzoom'))
                zoom = min(max(zlevels), maxzoom)
            else:
                # Compute at the maximum maxzoom (resolution of highest definition layer)
                zoom = max(zlevels)

        # Create object with final zoom value.
        try:
            obj = serializer.save(zoom=zoom, rasterlayers=rasterlayers)
        except IntegrityError:
            raise DuplicateError()

        # Push value count task to queue.
        compute_single_value_count_result.delay(obj.id)


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
