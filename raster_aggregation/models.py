from __future__ import unicode_literals

import datetime

from raster.models import Legend, RasterLayer
from raster.tiles.parser import rasterlayers_parser_ended
from raster.valuecount import Aggregator

from django.contrib.gis.db import models
from django.contrib.postgres.fields import HStoreField
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from raster_aggregation.utils import WEB_MERCATOR_SRID, convert_to_multipolygon


class AggregationLayer(models.Model):
    """
    Source data for aggregation layers and meta information.
    """
    name = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    shapefile = models.FileField(upload_to='shapefiles/aggregationlayers', blank=True, null=True)
    name_column = models.CharField(max_length=10, default='', blank=True)
    fields = HStoreField(blank=True, default={})
    min_zoom_level = models.IntegerField(default=0)
    max_zoom_level = models.IntegerField(default=18)
    simplification_tolerance = models.FloatField(default=0.01)
    parse_log = models.TextField(blank=True, null=True, default='')
    extent = models.PolygonField(srid=WEB_MERCATOR_SRID, editable=False, null=True)
    nr_of_areas = models.IntegerField(default=0, editable=False)
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


@receiver(pre_save, sender=AggregationLayer)
def reset_parse_log_if_data_changed(sender, instance, **kwargs):
    try:
        obj = AggregationLayer.objects.get(pk=instance.pk)
    except AggregationLayer.DoesNotExist:
        pass
    else:
        # If the filename has changed, clear parse status to trigger re-parsing.
        if (obj.shapefile.name != instance.shapefile.name):
            instance.parse_log = ''


@receiver(post_save, sender=AggregationLayer)
def parse_aggregation_layer_if_parselog_is_empty(sender, instance, created, **kwargs):
    from raster_aggregation.tasks import aggregation_layer_parser
    if instance.shapefile.name and not instance.parse_log:
        aggregation_layer_parser.delay(instance.id)


class AggregationLayerGroup(models.Model):
    """
    A set of aggregation layers to be used through the vector tile endpoint.
    The zoom level of each layer.
    """
    name = models.CharField(max_length=250)
    aggregationlayers = models.ManyToManyField(AggregationLayer, through='AggregationLayerZoomRange')

    def __str__(self):
        return self.name


class AggregationLayerZoomRange(models.Model):
    """
    Zoom range through which an aggregation layer should be available for display.
    """
    aggregationlayergroup = models.ForeignKey(AggregationLayerGroup, on_delete=models.CASCADE)
    aggregationlayer = models.ForeignKey(AggregationLayer, on_delete=models.CASCADE)
    min_zoom = models.IntegerField()
    max_zoom = models.IntegerField()

    class Meta:
        unique_together = ('aggregationlayergroup', 'aggregationlayer')

    def __str__(self):
        return 'Group {0} - Layer {1}'.format(
            self.aggregationlayergroup.name,
            self.aggregationlayer.name,
        )


class AggregationArea(models.Model):
    """
    Aggregation area polygons.
    """
    name = models.TextField(blank=True, null=True)
    aggregationlayer = models.ForeignKey(AggregationLayer, blank=True, null=True, on_delete=models.CASCADE)
    attributes = HStoreField(default={})
    geom = models.MultiPolygonField(srid=WEB_MERCATOR_SRID)
    geom_simplified = models.MultiPolygonField(srid=WEB_MERCATOR_SRID, blank=True, null=True)

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
    SCHEDULED = 0
    COMPUTING = 1
    FINISHED = 2
    FAILED = 3
    OUTDATED = 4

    STATUS = (
        (SCHEDULED, 'Scheduled'),
        (COMPUTING, 'Computing'),
        (FINISHED, 'Finished'),
        (FAILED, 'Failed'),
        (OUTDATED, 'Outdated'),
    )

    aggregationarea = models.ForeignKey(AggregationArea, on_delete=models.CASCADE)
    rasterlayers = models.ManyToManyField(RasterLayer)
    formula = models.TextField()
    layer_names = HStoreField()
    zoom = models.PositiveSmallIntegerField()
    units = models.TextField(default='')
    grouping = models.TextField(default='auto')
    value = HStoreField(default={})
    created = models.DateTimeField(auto_now=True)
    status = models.IntegerField(choices=STATUS, default=SCHEDULED)
    stats_min = models.FloatField(editable=False, blank=True, null=True)
    stats_max = models.FloatField(editable=False, blank=True, null=True)
    stats_avg = models.FloatField(editable=False, blank=True, null=True)
    stats_std = models.FloatField(editable=False, blank=True, null=True)

    stats_cumsum_t0 = models.FloatField(editable=False, blank=True, null=True, help_text='Nr of pixels counted.')
    stats_cumsum_t1 = models.FloatField(editable=False, blank=True, null=True, help_text='Sum of pixel values.')
    stats_cumsum_t2 = models.FloatField(editable=False, blank=True, null=True, help_text='Sum of squares of pixel values.')

    class Meta:
        unique_together = (
            'aggregationarea', 'formula', 'layer_names', 'zoom', 'units', 'grouping',
        )

    def __str__(self):
        return "{id} - {area}".format(id=self.id, area=self.aggregationarea.name)

    def populate(self):
        """
        Compute value count using the objects value count parameters.
        """
        # Update status
        self.status = self.COMPUTING
        self.save()

        try:
            # Compute aggregate result
            agg = Aggregator(
                layer_dict=self.layer_names,
                formula=self.formula,
                zoom=self.zoom,
                geom=self.aggregationarea.geom,
                acres=self.units.lower() == 'acres',
                grouping=self.grouping,
            )
            aggregation_result = agg.value_count()
            self.stats_min, self.stats_max, self.stats_avg, self.stats_std = agg.statistics()

            # Track cumulative data to be able to generalize stats over
            # multiple aggregation areas.
            self.stats_cumsum_t0 = agg._stats_t0
            self.stats_cumsum_t1 = agg._stats_t1
            self.stats_cumsum_t2 = agg._stats_t2

            # Convert values to string for storage in hstore
            self.value = {k: str(v) for k, v in aggregation_result.items()}

            self.status = self.FINISHED
        except:
            self.status = self.FAILED

        self.save()


@receiver(rasterlayers_parser_ended, sender=RasterLayer)
def remove_aggregation_results_after_rasterlayer_change(sender, instance, **kwargs):
    """
    Update the status of ValueCountResults that depend on the rasterlayer that was changed.
    """
    instance.valuecountresult_set.update(status=ValueCountResult.OUTDATED)
    ValueCountResult.objects.filter(rasterlayers=instance).update(status=ValueCountResult.OUTDATED)


@receiver(post_save, sender=Legend)
def remove_aggregation_results_after_legend_change(sender, instance, **kwargs):
    """
    Update the status of ValueCountResults that depend on the legend that was changed.
    """
    ValueCountResult.objects.filter(grouping=instance.id).update(status=ValueCountResult.OUTDATED)
