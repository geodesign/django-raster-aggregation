# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('raster_aggregation', '0003_make_hstore_extension'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='valuecountresult',
            name='aggregationarea',
        ),
        migrations.RemoveField(
            model_name='valuecountresult',
            name='rasterlayer',
        ),
        migrations.RemoveField(
            model_name='valuecountresult',
            name='value',
        ),
    ]
