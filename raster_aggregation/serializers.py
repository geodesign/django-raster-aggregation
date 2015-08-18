import json

from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from raster.models import RasterLayer, RasterLayerMetadata
from raster.valuecount import aggregator

from .models import AggregationArea


class MissingQueryParameter(APIException):
    status_code = 500
    default_detail = 'Missing Query Parameter.'


class AggregationAreaSerializer(serializers.ModelSerializer):

    geom = serializers.SerializerMethodField()

    class Meta:
        model = AggregationArea
        fields = ('id', 'name', 'geom')

    def get_geom(self, obj):
        obj.geom_simplified.transform(4326)
        return json.loads(obj.geom_simplified.geojson)


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

        # Look for required query parameters
        if 'zoom' not in request.GET:
            raise MissingQueryParameter(detail='Missing query parameter: zoom')
        elif 'formula' not in request.GET:
            raise MissingQueryParameter(detail='Missing query parameter: formula')
        elif 'layers' not in request.GET:
            raise MissingQueryParameter(detail='Missing query parameter: layers')

        # Compute tilerange for this area and the given zoom level
        zoom = int(request.GET.get('zoom'))

        # Get boolean to return data in acres if requested
        acres = 'acres' in request.GET

        # Get layer ids
        ids = request.GET.get('layers').split(',')

        # Parse layer ids into dictionary with variable names
        ids = {idx.split('=')[0]: idx.split('=')[1] for idx in ids}

        # Get formula from request
        formula = request.GET.get('formula')

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
