# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-06-26 05:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster_aggregation', '0014_auto_20170601_0550'),
    ]

    operations = [
        migrations.AddField(
            model_name='valuecountresult',
            name='stats_avg',
            field=models.FloatField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='valuecountresult',
            name='stats_max',
            field=models.FloatField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='valuecountresult',
            name='stats_min',
            field=models.FloatField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='valuecountresult',
            name='stats_std',
            field=models.FloatField(blank=True, editable=False, null=True),
        ),
    ]
