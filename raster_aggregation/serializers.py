import numpy
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from raster.models import RasterLayer, RasterLayerMetadata
from raster.valuecount import aggregator

from .models import AggregationArea, AggregationLayer


class AggregationAreaSimplifiedSerializer(serializers.ModelSerializer):

    geom = serializers.SerializerMethodField()

    class Meta:
        model = AggregationArea
        fields = ('id', 'name', 'geom')

    def get_geom(self, obj):
        # Transform geom to WGS84
        obj.geom_simplified.transform(4326)

        # Get coordinates and round to 4 digits
        coords = obj.geom_simplified.coords
        coords = [
            [numpy.around(numpy.array(y), 4) for y in x] for x in coords
        ]
        # Return data as geojson
        return {
            'type': 'MultiPolygon',
            'coordinates': coords
        }


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
        # Get request object
        request = self.context['request']

        # Get formula
        formula = request.GET.get('formula')

        # Get zoom level
        zoom = int(request.GET.get('zoom'))

        # Get boolean to return data in acres if requested
        acres = 'true' == request.GET.get('acres', '').lower()

        # Get layer ids
        ids = request.GET.get('layers').split(',')

        # Parse layer ids into dictionary with variable names
        ids = {idx.split('=')[0]: idx.split('=')[1] for idx in ids}

        return aggregator(ids, zoom, obj.geom, formula, acres)


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


class AggregationLayerSerializer(serializers.ModelSerializer):

    nr_of_areas = serializers.SerializerMethodField()

    class Meta:
        model = AggregationLayer
        fields = ('id', 'name', 'description', 'min_zoom_level', 'max_zoom_level', 'nr_of_areas')

    def get_nr_of_areas(self, obj):
        return obj.aggregationarea_set.count()
