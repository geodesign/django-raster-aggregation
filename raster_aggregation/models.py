from __future__ import unicode_literals

import datetime

from raster.models import Legend, RasterLayer
from raster.tiles.parser import rasterlayers_parser_ended
from raster.valuecount import Aggregator

from django.contrib.gis.db import models
from django.contrib.postgres.fields import HStoreField
from django.db.models.signals import post_save
from django.dispatch import receiver
from raster_aggregation.utils import WEB_MERCATOR_SRID, convert_to_multipolygon


class AggregationLayer(models.Model):
    """
    Source data for aggregation layers and meta information.
    """
    UNPROCESSED = 'Unprocessed'
    PENDING = 'Pending'
    PROCESSING = 'Processing'
    FINISHED = 'Finished'
    FAILED = 'Failed'
    ST_STATUS_CHOICES = (
        (UNPROCESSED, UNPROCESSED),
        (PENDING, PENDING),
        (PROCESSING, PROCESSING),
        (FINISHED, FINISHED),
        (FAILED, FAILED),
    )
    name = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    shapefile = models.FileField(upload_to='shapefiles/aggregationlayers', blank=True, null=True)
    name_column = models.CharField(max_length=10, default='', blank=True)
    fields = HStoreField(blank=True, default=dict)
    min_zoom_level = models.IntegerField(default=0)
    max_zoom_level = models.IntegerField(default=18)
    simplification_tolerance = models.FloatField(default=0.01)
    parse_log = models.TextField(blank=True, null=True, default='')
    extent = models.PolygonField(srid=WEB_MERCATOR_SRID, editable=False, null=True)
    nr_of_areas = models.IntegerField(default=0, editable=False)
    modified = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=ST_STATUS_CHOICES, default=UNPROCESSED)

    def __str__(self):
        return '{name} ({count} divisions | {status})'.format(
            name=self.name,
            count=self.aggregationarea_set.all().count(),
            status=self.status,
        )

    def log(self, msg, status=None):
        """
        Write a message to the parse log of the aggregationlayer instance.
        """
        # Prepare datetime stamp for log
        now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))
        # Update status if requested.
        if status:
            self.status = status
        # Ensure log is not null.
        if not self.parse_log:
            self.parse_log = ''
        # Write log message.
        self.parse_log += '\n' + now + msg
        self.save()


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
    attributes = HStoreField(default=dict, blank=True)
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
    range_min = models.FloatField(blank=True, null=True, help_text='Lower cutoff limit for valuecounts. Only used if upper cutoff is also specified.')
    range_max = models.FloatField(blank=True, null=True, help_text='Upper cutoff limit for valuecounts. Only used if lower cutoff is also specified.')

    value = HStoreField(default=dict, db_index=True)
    created = models.DateTimeField(auto_now=True)
    status = models.IntegerField(choices=STATUS, default=SCHEDULED)
    stats_min = models.FloatField(editable=False, blank=True, null=True, db_index=True)
    stats_max = models.FloatField(editable=False, blank=True, null=True, db_index=True)
    stats_avg = models.FloatField(editable=False, blank=True, null=True, db_index=True)
    stats_std = models.FloatField(editable=False, blank=True, null=True, db_index=True)

    stats_cumsum_t0 = models.FloatField(editable=False, blank=True, null=True, help_text='Nr of pixels counted.')
    stats_cumsum_t1 = models.FloatField(editable=False, blank=True, null=True, help_text='Sum of pixel values.')
    stats_cumsum_t2 = models.FloatField(editable=False, blank=True, null=True, help_text='Sum of squares of pixel values.')

    class Meta:
        unique_together = (
            'aggregationarea', 'formula', 'layer_names', 'zoom', 'units', 'grouping',
        )

    def __str__(self):
        return "{id} - {area}".format(id=self.id, area=self.aggregationarea.name)

    def populate(self, save=True):
        """
        Compute value count using the objects value count parameters.
        """
        # Update status
        self.status = self.COMPUTING
        if save:
            self.save()

        # Compute range for valuecounts if provided.
        if self.range_min is not None and self.range_max is not None:
            hist_range = (self.range_min, self.range_max)
        else:
            hist_range = None

        try:
            # Compute aggregate result.
            agg = Aggregator(
                layer_dict=self.layer_names,
                formula=self.formula,
                zoom=self.zoom,
                geom=self.aggregationarea.geom,
                acres=self.units.lower() == 'acres',
                grouping=self.grouping,
                hist_range=hist_range,
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

        if save:
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
