# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster_aggregation', '0009_auto_20151013_0255'),
    ]

    operations = [
        migrations.AddField(
            model_name='valuecountresult',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2015, 10, 15, 5, 14, 38, 422561), auto_now=True),
            preserve_default=False,
        ),
    ]
