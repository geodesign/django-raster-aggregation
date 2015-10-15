import datetime

from django.contrib.gis.db import models
from django.contrib.postgres.fields import HStoreField
from django.dispatch import receiver
from raster.models import RasterLayer
from raster.parser import rasterlayers_parser_ended
from raster.valuecount import aggregator

from .parser import AggregationDataParser
from .utils import WEB_MERCATOR_SRID, convert_to_multipolygon


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
        """
        Reduce the geometries to simplified version.
        """
        geom = self.geom.simplify(
            tolerance=self.aggregationlayer.simplification_tolerance,
            preserve_topology=True
        )
        geom = convert_to_multipolygon(geom)
        self.geom_simplified = geom
        super(AggregationArea, self).save(*args, **kwargs)


class ValueCountResult(models.Model):
    """
    A class to store precomputed aggregation values from raster layers.
    """
    aggregationarea = models.ForeignKey(AggregationArea)
    rasterlayers = models.ManyToManyField(RasterLayer)
    formula = models.TextField()
    layer_names = HStoreField()
    zoom = models.PositiveSmallIntegerField()
    units = models.TextField(default='')
    grouping = models.TextField(default='auto')
    value = HStoreField()
    created = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (
            'aggregationarea', 'formula', 'layer_names', 'zoom', 'units', 'grouping',
        )

    def __str__(self):
        return "{id} - {area}".format(id=self.id, area=self.aggregationarea.name)

    def save(self, *args, **kwargs):
        """
        Compute value count on save using the objects value count parameters.
        """
        # Compute aggregate result
        aggregation_result = aggregator(
            self.layer_names,
            self.zoom,
            self.aggregationarea.geom,
            self.formula,
            self.units.lower() == 'acres',
            self.grouping
        )

        # Convert values to string for storage in hstore
        self.value = {k: str(v) for k, v in aggregation_result.items()}

        # Save value count result data
        super(ValueCountResult, self).save(*args, **kwargs)

        # Add raster layers for tracking change and subsequent invalidation
        # of value count results. The rasterlayer praser start signal will use
        # this information to remove all outdated value count results on
        # reparse of raster layers.
        for layer_id in self.layer_names.values():
            lyr = RasterLayer.objects.get(id=layer_id)
            self.rasterlayers.add(lyr)


@receiver(rasterlayers_parser_ended, sender=RasterLayer)
def remove_aggregation_results_after_rasterlayer_change(sender, instance, **kwargs):
    """
    Delete ValueCountResults that depend on the rasterlayer that was changed.
    """
    ValueCountResult.objects.filter(rasterlayers=instance).delete()
