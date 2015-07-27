import json
from collections import Counter

import numpy
from rest_framework import filters, viewsets
from rest_framework.settings import api_settings
from rest_framework_csv import renderers
from rest_framework_gis.filters import InBBOXFilter

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View
from raster import tiler
from raster.formulas import RasterAlgebraParser
from raster.models import RasterTile
from raster.rasterize import rasterize
from raster_aggregation.models import AggregationArea
from raster_aggregation.serializers import AggregationAreaSerializer, AggregationAreaExportSerializer, AggregationAreaGeoSerializer


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
        # Get aggregation area
        area_id = self.kwargs.get('area')
        area = get_object_or_404(AggregationArea, id=area_id)

        # Compute tilerange for this area and the given zoom level
        zoom = int(request.GET.get('zoom'))
        tilerange = tiler.tile_index_range(area.geom.extent, zoom)

        # Get layer ids
        ids = request.GET.get('layers').split(',')

        # Parse layer ids into dictionary with variable names
        ids = {idx.split('=')[0]: idx.split('=')[1] for idx in ids}

        # Get formula from request
        formula = request.GET.get('formula')

        # Loop through tiles and evaluate raster algebra for each tile
        results = Counter({})
        for tilex in range(tilerange[0], tilerange[2] + 1):
            for tiley in range(tilerange[1], tilerange[3] + 1):
                # Prepare a data dictionary with named tiles for algebra evaluation
                data = {}
                for name, layerid in ids.items():
                    tile = RasterTile.objects.filter(
                        tilex=tilex,
                        tiley=tiley,
                        tilez=zoom,
                        rasterlayer_id=layerid
                    ).first()
                    if tile:
                        data[name] = tile.rast
                    else:
                        # Ignore this tile if any layer has no data for it
                        break

                if data != {}:
                    # Evaluate algebra on tiles
                    result = self.parser.evaluate_raster_algebra(data, formula, mask=True)

                    # Rasterize the aggregation area to the result raster
                    rastgeom = rasterize(area.geom, result)

                    # Compute unique counts constrained with the rasterized geom
                    result = numpy.unique(result.bands[0].data()[rastgeom.bands[0].data() == 1], return_counts=True)

                    # Add counts to results
                    results += Counter(dict(zip(result[0], result[1])))

        # Prepare data for json response
        results = json.dumps({str(k): v for k, v in results.iteritems()})

        return HttpResponse(results, content_type='application/json')


class AggregationAreaViewSet(viewsets.ModelViewSet):
    """
    Regular aggregation Area model view endpoint.
    """
    serializer_class = AggregationAreaSerializer
    allowed_methods = ('GET', )

    def get_queryset(self):
        return AggregationArea.objects.all()


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
