# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster_aggregation', '0007_valuecountresult_grouping'),
    ]

    operations = [
        migrations.AlterField(
            model_name='valuecountresult',
            name='zoom',
            field=models.PositiveSmallIntegerField(null=True, blank=True),
        ),
    ]
