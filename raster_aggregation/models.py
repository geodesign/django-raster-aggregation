"""
Models for storing and parsing aggregation layer shape files
"""
import json

from django.contrib.gis.db import models
from raster.models import RasterLayer
from raster_aggregation.utils import convert_to_multipolygon

from .mixins import AggregationDataParser


class AggregationLayer(models.Model, AggregationDataParser):
    """
    Source data for aggregation layers and meta information.
    """

    name = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    shapefile = models.FileField(upload_to='shapefiles/aggregationlayers')
    name_column = models.CharField(max_length=10)
    min_zoom_level = models.IntegerField(default=0)
    max_zoom_level = models.IntegerField(default=18)
    simplification_tolerance = models.FloatField(default=0.01)
    parse_log = models.TextField(blank=True, null=True, default='')

    def __unicode__(self):
        return '{name} ({count} divisions)'.format(name=self.name,
                            count=self.aggregationarea_set.all().count())


class AggregationArea(models.Model):
    """
    Aggregation area polygons.
    """

    name = models.TextField(blank=True, null=True)
    aggregationlayer = models.ForeignKey(AggregationLayer, blank=True, null=True)
    geom = models.MultiPolygonField()
    geom_simplified = models.MultiPolygonField(blank=True, null=True)
    objects = models.GeoManager()

    def __unicode__(self):
        return "{lyr} Aggregate-Area".format(lyr=self.aggregationlayer.name)

    def save(self, *args, **kwargs):
        # Reduce the geometries to simplified version
        geom = self.geom
        tol = self.aggregationlayer.simplification_tolerance
        geom = geom.simplify(tolerance=tol, preserve_topology=True)
        geom = convert_to_multipolygon(geom)
        self.geom_simplified = geom
        super(AggregationArea, self).save(*args, **kwargs)

    def get_value_count(self, rasterlayer_id):
        if rasterlayer_id:

            try:
                rasterlayer_id = int(rasterlayer_id)
            except:
                return {}

            result = self.valuecountresult_set.filter(
                rasterlayer_id=rasterlayer_id)
            if result:
                return json.loads(result[0].value)
        return {}


class ValueCountResult(models.Model):
    """
    A class to store precomputed value counts from raster layers.
    """
    rasterlayer = models.ForeignKey(RasterLayer)
    aggregationarea = models.ForeignKey(AggregationArea)
    value = models.TextField()
