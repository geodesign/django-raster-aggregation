# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster_aggregation', '0006_auto_20150922_1030'),
    ]

    operations = [
        migrations.AddField(
            model_name='valuecountresult',
            name='grouping',
            field=models.TextField(default=b'auto'),
        ),
    ]
