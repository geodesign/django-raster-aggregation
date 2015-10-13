# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def drop_valuecounts_with_zoom_null_forward(apps, schema_editor):
    """
    Delete value count results with null values.
    """
    ValueCountResult = apps.get_model("raster_aggregation", "ValueCountResult")
    ValueCountResult.objects.filter(zoom__isnull=True).delete()


def drop_valuecounts_with_zoom_null_backward(apps, schema_editor):
    """
    The backwards migration does not need to do anything.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('raster_aggregation', '0008_auto_20151007_0635'),
    ]

    operations = [
        migrations.RunPython(
            drop_valuecounts_with_zoom_null_forward,
            drop_valuecounts_with_zoom_null_backward,
        ),
        migrations.AlterField(
            model_name='valuecountresult',
            name='zoom',
            field=models.PositiveSmallIntegerField(),
        ),
        migrations.AlterUniqueTogether(
            name='valuecountresult',
            unique_together=set([('aggregationarea', 'formula', 'layer_names', 'zoom', 'units', 'grouping')]),
        ),
    ]
