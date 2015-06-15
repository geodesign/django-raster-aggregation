# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.contrib.gis.db.models.fields
import raster_aggregation.mixins
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0011_auto_20150615_0800'),
    ]

    operations = [
        migrations.CreateModel(
            name='AggregationArea',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.TextField(null=True, blank=True)),
                ('geom', django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326)),
                ('geom_simplified', django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326, null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='AggregationLayer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, null=True, blank=True)),
                ('description', models.TextField(null=True, blank=True)),
                ('shapefile', models.FileField(upload_to=b'shapefiles/aggregationlayers')),
                ('name_column', models.CharField(max_length=10)),
                ('min_zoom_level', models.IntegerField(default=0)),
                ('max_zoom_level', models.IntegerField(default=18)),
                ('simplification_tolerance', models.FloatField(default=0.01)),
                ('parse_log', models.TextField(default=b'', null=True, blank=True)),
            ],
            bases=(models.Model, raster_aggregation.mixins.AggregationDataParser),
        ),
        migrations.CreateModel(
            name='ValueCountResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.TextField()),
                ('aggregationarea', models.ForeignKey(to='raster_aggregation.AggregationArea')),
                ('rasterlayer', models.ForeignKey(to='raster.RasterLayer')),
            ],
        ),
        migrations.AddField(
            model_name='aggregationarea',
            name='aggregationlayer',
            field=models.ForeignKey(blank=True, to='raster_aggregation.AggregationLayer', null=True),
        ),
    ]
