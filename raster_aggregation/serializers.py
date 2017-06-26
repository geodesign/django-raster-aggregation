from __future__ import unicode_literals

import numpy
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from raster_aggregation.models import AggregationArea, AggregationLayer, ValueCountResult


class AggregationAreaSerializer(serializers.ModelSerializer):

    class Meta:
        model = AggregationArea
        fields = ('id', 'name', 'geom', 'aggregationlayer')


class AggregationAreaSimplifiedSerializer(AggregationAreaSerializer):

    geom = serializers.SerializerMethodField()

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

    class Meta:
        model = AggregationArea
        geo_field = 'geom_simplified'
        fields = ('id', 'name', 'aggregationlayer')


class ValueCountResultSerializer(serializers.ModelSerializer):

    rasterlayers = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    value = serializers.SerializerMethodField()
    zoom = serializers.IntegerField(default=-1)
    status = serializers.CharField(source='get_status_display', read_only=True)
    min = serializers.FloatField(source='stats_min', read_only=True)
    max = serializers.FloatField(source='stats_max', read_only=True)
    avg = serializers.FloatField(source='stats_avg', read_only=True)
    std = serializers.FloatField(source='stats_std', read_only=True)

    class Meta:
        model = ValueCountResult
        fields = (
            'id', 'aggregationarea', 'rasterlayers', 'formula', 'layer_names',
            'zoom', 'units', 'grouping', 'value', 'created', 'status',
            'min', 'max', 'avg', 'std',
        )
        read_only_fields = ('id', 'value', 'created', 'status', 'rasterlayers',)

    def get_value(self, obj):
        """
        Convert keys to strings and hstore values to floats.
        """
        return {str(k): float(v) for k, v in obj.value.items()}


class AggregationLayerSerializer(serializers.ModelSerializer):

    nr_of_areas = serializers.SerializerMethodField()
    aggregationareas = serializers.PrimaryKeyRelatedField(many=True, read_only=True, source='aggregationarea_set')

    class Meta:
        model = AggregationLayer
        fields = (
            'id', 'name', 'description', 'min_zoom_level', 'max_zoom_level',
            'nr_of_areas', 'shapefile', 'name_column',
            'simplification_tolerance', 'parse_log', 'modified',
            'aggregationareas',
        )
        read_only_fields = ('nr_of_areas', 'parse_log', 'modified', )

    def get_nr_of_areas(self, obj):
        return obj.aggregationarea_set.count()
