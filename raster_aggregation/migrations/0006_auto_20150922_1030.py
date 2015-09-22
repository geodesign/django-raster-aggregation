# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('raster_aggregation', '0005_auto_20150915_1207'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='valuecountresult',
            unique_together=set([('aggregationarea', 'formula', 'layer_names', 'zoom', 'units')]),
        ),
    ]
