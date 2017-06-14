from __future__ import unicode_literals

import mapbox_vector_tile
from raster.models import RasterLayer
from raster.tiles.const import WEB_MERCATOR_SRID
from raster.tiles.utils import tile_bounds
from rest_framework import filters, viewsets
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework_gis.filters import InBBOXFilter

from django.contrib.gis.db.models.functions import Intersection, Transform
from django.contrib.gis.gdal import OGRGeometry
from django.db import IntegrityError
from django.http import Http404, HttpResponse
from django.views.generic import View
from raster_aggregation.exceptions import DuplicateError
from raster_aggregation.filters import ValueCountResultFilter
from raster_aggregation.models import AggregationArea, AggregationLayer, AggregationLayerGroup, ValueCountResult
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
    filter_backends = (filters.DjangoFilterBackend, )
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


class VectorTilesView(View):

    def get(self, request, layergroup, x, y, z, response_format, *args, **kwargs):
        # Select which agglayer to use for this tile.
        grp = AggregationLayerGroup.objects.get(id=layergroup)
        layerzoomrange = grp.aggregationlayerzoomrange_set.filter(
            min_zoom__lte=z,
            max_zoom__gte=z,
        ).first()
        if not layerzoomrange:
            raise Http404('No layer found for this zoom level')
        lyr = layerzoomrange.aggregationlayer

        # Compute intersection between the tile boundary and the layer geometries.
        bounds = tile_bounds(int(x), int(y), int(z))
        bounds = OGRGeometry.from_bbox(bounds)
        bounds.srid = WEB_MERCATOR_SRID
        bounds = bounds.geos
        result = AggregationArea.objects.filter(
            aggregationlayer=lyr,
            geom__intersects=bounds,
        ).annotate(
            intersection=Transform(Intersection('geom', bounds), WEB_MERCATOR_SRID)
        ).only('id', 'name')

        # Render intersection as vector tile in two different available formats.
        if response_format == '.json':
            result = ['{{"geometry": {0}, "properties": {{"id": {1}, "name": "{2}"}}}}'.format(dat.intersection.geojson, dat.id, dat.name) for dat in result]
            result = ','.join(result)
            result = '{"type": "FeatureCollection","features":[' + result + ']}'
            return HttpResponse(result, content_type="application/json")
        elif response_format == '.pbf':
            result = [{"geometry": bytes(dat.intersection.wkb), "properties": {"id": dat.id, "name": dat.name}} for dat in result]
            result = mapbox_vector_tile.encode({"name": "testlayer", "features": result})
            return HttpResponse(result, content_type="application/octet-stream")
        else:
            raise Http404('Unknown response format {0}'.format(response_format))
