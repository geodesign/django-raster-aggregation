# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster_aggregation', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='aggregationlayer',
            name='modified',
            field=models.DateTimeField(default=datetime.datetime(2015, 8, 19, 3, 21, 37, 99924), auto_now=True),
            preserve_default=False,
        ),
    ]
