from collections import Counter

import numpy
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from raster import tiler
from raster.formulas import RasterAlgebraParser
from raster.models import RasterLayer, RasterLayerMetadata, RasterTile
from raster.rasterize import rasterize

from .models import AggregationArea


class AggregationAreaSerializer(serializers.ModelSerializer):

    geom = serializers.SerializerMethodField()

    class Meta:
        model = AggregationArea
        fields = ('id', 'name', 'geom', 'geom_simplified')

    def get_geom(self, obj):
        geom = obj.geom_simplified
        geom.transform(4326)
        return geom.coords


class AggregationAreaGeoSerializer(GeoFeatureModelSerializer):

    valuecount = serializers.SerializerMethodField('get_value_count')

    class Meta:
        model = AggregationArea
        geo_field = 'geom_simplified'
        fields = ('id', 'name', 'aggregationlayer', 'valuecount')

    def get_value_count(self, obj):
        rasterlayer_id = self.context['request'].QUERY_PARAMS.get(
            'rasterlayer_id', None)
        return obj.get_value_count(rasterlayer_id)


class AggregationAreaValueSerializer(serializers.ModelSerializer):

    value = serializers.SerializerMethodField()

    class Meta:
        model = AggregationArea
        fields = ('id', 'value')

    def get_value(self, obj):
        """
        Return value count for this aggregation area and an algebra expression.

        Should currently only be used with categorical rasters, as it will look
        for unique values.
        """
        parser = RasterAlgebraParser()

        request = self.context['request']

        # Compute tilerange for this area and the given zoom level
        zoom = int(request.GET.get('zoom'))
        tilerange = tiler.tile_index_range(obj.geom.extent, zoom)

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
                    result = parser.evaluate_raster_algebra(data, formula, mask=True)

                    # Rasterize the aggregation area to the result raster
                    rastgeom = rasterize(obj.geom, result)

                    # Compute unique counts constrained with the rasterized geom
                    result = numpy.unique(result.bands[0].data()[rastgeom.bands[0].data() == 1], return_counts=True)

                    # Add counts to results
                    results += Counter(dict(zip(result[0], result[1])))

        # Transform pixel count to acres if requested
        scaling_factor = 1
        if 'acres' in request.GET:
            scaling_factor = int(round(abs(rastgeom.scale.x * rastgeom.scale.y) * 0.000247105381))

        results = {str(k): v * scaling_factor for k, v in results.iteritems()}

        return results


class AggregationAreaExportSerializer(serializers.ModelSerializer):

    value_acres = serializers.SerializerMethodField('get_area_acres')
    aggregatelayer = serializers.SerializerMethodField('get_agglayer_name')
    rasterlayer = serializers.SerializerMethodField('get_rasterlayer_name')

    class Meta:
        model = AggregationArea
        fields = ('aggregatelayer', 'rasterlayer', 'name', 'value_acres')

    def get_area_acres(self, obj):
        """
        Assumptions: The unit of the pixel scale is Meters. This provides wrong
        data for rasters that are not in meter units.
        """
        # Create name dict from wms_classes
        # TODO: Update this with dynamic rendering from django-raster
        names = {}
        for cat in []:
            names[cat['expression']] = cat['name']

        # Get count object
        rasterlayer_id = self.context['request'].QUERY_PARAMS.get(
            'rasterlayer_id', None)
        rstmet = RasterLayerMetadata.objects.get(rasterlayer_id=rasterlayer_id)

        # Cast counts to more useful measures (acres)
        count = obj.get_value_count(rasterlayer_id)
        warped = {}
        for x in count:
            lc_class_name = names.get(str(int(x['value'])), None)
            if lc_class_name:
                warped[lc_class_name] = int(int(x['count']) * abs(rstmet.scalex * rstmet.scaley) / 4046.8564224)
        return warped

    def get_agglayer_name(self, obj):
        return obj.aggregationlayer.name

    def get_rasterlayer_name(self, obj):
        rasterlayer_id = self.context['request'].QUERY_PARAMS.get('rasterlayer_id', None)
        return RasterLayer.objects.get(id=rasterlayer_id).name
