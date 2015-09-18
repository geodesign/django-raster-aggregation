# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.contrib.postgres.fields.hstore
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0015_auto_20150819_0320'),
        ('raster_aggregation', '0004_auto_20150915_1206'),
    ]

    operations = [
        migrations.AddField(
            model_name='valuecountresult',
            name='formula',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='valuecountresult',
            name='layer_names',
            field=django.contrib.postgres.fields.hstore.HStoreField(default={}),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='valuecountresult',
            name='rasterlayers',
            field=models.ManyToManyField(to='raster.RasterLayer'),
        ),
        migrations.AddField(
            model_name='valuecountresult',
            name='units',
            field=models.TextField(default=b''),
        ),
        migrations.AddField(
            model_name='valuecountresult',
            name='value',
            field=django.contrib.postgres.fields.hstore.HStoreField(default={}),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='valuecountresult',
            name='zoom',
            field=models.PositiveSmallIntegerField(default=0),
            preserve_default=False,
        ),
    ]
