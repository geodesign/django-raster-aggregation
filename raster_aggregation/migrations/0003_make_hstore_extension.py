# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.postgres.operations import HStoreExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('raster_aggregation', '0002_aggregationlayer_modified'),
    ]

    operations = [
        HStoreExtension(),
    ]
