import datetime
import json

from django.contrib.gis.db import models
from raster.models import RasterLayer
from raster_aggregation.aggregator import Aggregator
from raster_aggregation.parser import AggregationDataParser
from raster_aggregation.utils import WEB_MERCATOR_SRID, convert_to_multipolygon


class AggregationLayer(models.Model, AggregationDataParser, Aggregator):
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
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '{name} ({count} divisions)'.format(
            name=self.name,
            count=self.aggregationarea_set.all().count()
        )

    def log(self, msg, reset=False):
        """
        Write a message to the parse log of the aggregationlayer instance.
        """
        # Prepare datetime stamp for log
        now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))

        # Write log, reset if requested
        if reset:
            self.parse_log = now + msg
        else:
            self.parse_log += '\n' + now + msg

        self.save()


class AggregationArea(models.Model):
    """
    Aggregation area polygons.
    """
    name = models.TextField(blank=True, null=True)
    aggregationlayer = models.ForeignKey(AggregationLayer, blank=True, null=True)
    geom = models.MultiPolygonField(srid=WEB_MERCATOR_SRID)
    geom_simplified = models.MultiPolygonField(srid=WEB_MERCATOR_SRID, blank=True, null=True)
    objects = models.GeoManager()

    def __str__(self):
        return "{lyr} - {name}".format(lyr=self.aggregationlayer.name, name=self.name)

    def save(self, *args, **kwargs):
        # Reduce the geometries to simplified version
        geom = self.geom
        tol = self.aggregationlayer.simplification_tolerance
        geom = geom.simplify(tolerance=tol, preserve_topology=True)
        geom = convert_to_multipolygon(geom)
        self.geom_simplified = geom
        super(AggregationArea, self).save(*args, **kwargs)

    def get_value_count(self, rasterlayer_id):
        data = {}
        if rasterlayer_id:
            result = self.valuecountresult_set.filter(
                rasterlayer_id=rasterlayer_id
            )

            if result.exists():
                data = json.loads(result[0].value)

        return data


class ValueCountResult(models.Model):
    """
    A class to store precomputed value counts from raster layers.
    """
    rasterlayer = models.ForeignKey(RasterLayer)
    aggregationarea = models.ForeignKey(AggregationArea)
    value = models.TextField()

    def __str__(self):
        return "{id} - {area}".format(id=self.id, area=self.aggregationarea.name)
