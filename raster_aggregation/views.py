from __future__ import unicode_literals

import mapbox_vector_tile
from django_filters.rest_framework import DjangoFilterBackend
from raster.models import RasterLayer
from raster.tiles.const import WEB_MERCATOR_SRID
from raster.tiles.utils import tile_bounds
from rest_framework import viewsets
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework_gis.filters import InBBOXFilter

from django.contrib.gis.db.models.functions import Intersection
from django.contrib.gis.gdal import OGRGeometry
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from raster_aggregation.exceptions import DuplicateError
from raster_aggregation.filters import ValueCountResultFilter
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
    filter_backends = (DjangoFilterBackend, )
    filter_fields = ('aggregationlayer', )


class ValueCountResultViewSet(CreateModelMixin,
                              RetrieveModelMixin,
                              DestroyModelMixin,
                              ListModelMixin,
                              viewsets.GenericViewSet):
    """
    Regular aggregation Area model view endpoint.
    """
    queryset = ValueCountResult.objects.all()
    serializer_class = ValueCountResultSerializer
    filter_backends = (DjangoFilterBackend, )
    filter_class = ValueCountResultFilter

    def perform_create(self, serializer):
        # Get list of rasterlayers based on layer names dict.
        rasterlayers = [RasterLayer.objects.get(id=pk) for pk in set(serializer.validated_data.get('layer_names').values())]

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
        if 'synchronous' in self.request.GET:
            compute_single_value_count_result(obj.id)
            obj.refresh_from_db()
        else:
            compute_single_value_count_result.delay(obj.id)


class AggregationAreaGeoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that returns Aggregation Area geometries in GeoJSON format.
    """
    serializer_class = AggregationAreaGeoSerializer
    allowed_methods = ('GET', )
    filter_backends = (InBBOXFilter, DjangoFilterBackend, )
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


class AggregationLayerVectorTilesViewSet(ListModelMixin, viewsets.GenericViewSet):

    queryset = AggregationLayer.objects.all()

    def list(self, request, aggregationlayer, x, y, z, frmt, *args, **kwargs):
        # Select which agglayer to use for this tile.
        lyr = get_object_or_404(AggregationLayer, pk=aggregationlayer)

        # Compute tile boundary coorner coordinates.
        bounds_coords = tile_bounds(int(x), int(y), int(z))

        # Create a geometry with a 1% buffer around the tile. This buffered
        # tile boundary will be used for clipping the geometry. The overflow
        # will visually dissolve the polygons on the frontend visualization.
        bounds = OGRGeometry.from_bbox(bounds_coords)
        bounds.srid = WEB_MERCATOR_SRID
        bounds = bounds.geos
        bounds_buffer = bounds.buffer((bounds_coords[2] - bounds_coords[0]) / 100)

        # Get the intersection of the aggregation areas and the tile boundary.
        # use buffer to clip the aggregation area.
        result = AggregationArea.objects.filter(
            aggregationlayer=lyr,
            geom__intersects=bounds,
        ).annotate(
            intersection=Intersection('geom', bounds_buffer)
        ).only('id', 'name')

        # Render intersection as vector tile in two different available formats.
        if frmt == 'json':
            result = ['{{"geometry": {0}, "properties": {{"id": {1}, "name": "{2}"}}}}'.format(dat.intersection.geojson, dat.id, dat.name) for dat in result]
            result = ','.join(result)
            result = '{"type": "FeatureCollection","features":[' + result + ']}'
            return HttpResponse(result, content_type="application/json")
        elif frmt == 'pbf':
            features = [
                {
                    "geometry": bytes(dat.intersection.wkb),
                    "properties": {
                        "id": dat.id,
                        "name": dat.name,
                        "attributes": dat.attributes,
                    },
                } for dat in result
            ]
            data = [
                {
                    "name": lyr.name,
                    "features": features,
                },
            ]
            vtile = mapbox_vector_tile.encode(data, quantize_bounds=bounds_coords)
            return HttpResponse(vtile, content_type='application/x-protobuf')
