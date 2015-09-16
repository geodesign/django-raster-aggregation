import numpy
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import AggregationArea, AggregationLayer, ValueCountResult


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
        acres = 'acres' if request.GET.has_key('acres') else ''

        # Get layer ids
        ids = request.GET.get('layers').split(',')

        # Parse layer ids into dictionary with variable names
        ids = {idx.split('=')[0]: idx.split('=')[1] for idx in ids}

        result, created = ValueCountResult.objects.get_or_create(
            aggregationarea=obj,
            formula=formula,
            layer_names=ids,
            zoom=zoom,
            units=acres
        )

        return result.value


class AggregationLayerSerializer(serializers.ModelSerializer):

    nr_of_areas = serializers.SerializerMethodField()

    class Meta:
        model = AggregationLayer
        fields = ('id', 'name', 'description', 'min_zoom_level', 'max_zoom_level', 'nr_of_areas')

    def get_nr_of_areas(self, obj):
        return obj.aggregationarea_set.count()
