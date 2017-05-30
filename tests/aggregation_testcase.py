from __future__ import unicode_literals

import inspect
import os
import shutil
import tempfile

import numpy
from raster.models import Legend, LegendEntry, LegendSemantics, RasterLayer

from django.core.files import File
from django.test import TestCase
from raster_aggregation.models import AggregationLayer
from raster_aggregation.tasks import aggregation_layer_parser


class RasterAggregationTestCase(TestCase):

    def setUp(self):
        # Instantiate Django file instances with nodes and links
        self.pwd = os.path.dirname(
            os.path.abspath(
                inspect.getfile(inspect.currentframe())
            )
        )

        self.rasterfile = File(open(os.path.join(self.pwd, 'data/raster.tif.zip'), 'rb'), name='raster.tif.zip')
        shapefile = File(open(os.path.join(self.pwd, 'data/shapefile.zip'), 'rb'), name='shapefile.zip')

        self.media_root = tempfile.mkdtemp()

        with self.settings(MEDIA_ROOT=self.media_root):
            # Create raster layer
            self.rasterlayer = RasterLayer.objects.create(
                name='Raster data',
                description='Small raster for testing',
                datatype='ca',
                nodata='0',
                rasterfile=self.rasterfile
            )
            self.empty_rasterlayer = RasterLayer.objects.create(
                name='Raster data',
                description='Small raster for testing',
                datatype='ca',
                nodata='0',
                rasterfile=self.rasterfile
            )
            self.empty_rasterlayer.rastertile_set.all().delete()

            # Create aggregation layer
            self.agglayer = AggregationLayer.objects.create(
                name='abc',
                name_column='name',
                shapefile=shapefile
            )
            # Parse aggregation layer
            aggregation_layer_parser(self.agglayer.id)

        # Create legend semantics.
        sem1 = LegendSemantics.objects.create(name='Earth')
        sem2 = LegendSemantics.objects.create(name='Wind')
        sem3 = LegendSemantics.objects.create(name='Fire')

        # Create legends.
        self.legend_float = Legend.objects.create(title='Float key legend')
        LegendEntry.objects.create(semantics=sem1, expression='4', color='#123456', legend=self.legend_float, code='1')
        LegendEntry.objects.create(semantics=sem2, expression='2', color='#654321', legend=self.legend_float, code='2')

        self.legend_exp = Legend.objects.create(title='Expression key legend')
        LegendEntry.objects.create(semantics=sem3, expression='(x >= 2) & (x < 5)', color='#123456', legend=self.legend_exp, code='1')

        # Compute expected totals from numpy value count
        self.expected = {}
        for tile in self.rasterlayer.rastertile_set.filter(tilez=11):
            val, counts = numpy.unique(tile.rast.bands[0].data(), return_counts=True)
            for pair in zip(val, counts):
                if str(pair[0]) in self.expected:
                    self.expected[str(pair[0])] += pair[1]
                else:
                    self.expected[str(pair[0])] = pair[1]

        # Pop the nodata value, aggregation values are computed on masked arrays
        self.expected.pop('0')

    def tearDown(self):
        shutil.rmtree(self.media_root)
