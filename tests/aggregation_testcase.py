import inspect
import os
import shutil
import tempfile

import numpy

from django.core.files import File
from django.test import TestCase
from raster.models import RasterLayer
from raster_aggregation.models import AggregationLayer


class RasterAggregationTestCase(TestCase):

    def setUp(self):
        # Instantiate Django file instances with nodes and links
        self.pwd = os.path.dirname(
            os.path.abspath(
                inspect.getfile(inspect.currentframe())
            )
        )

        rasterfile = File(open(os.path.join(self.pwd, 'data/raster.tif.zip')))
        shapefile = File(open(os.path.join(self.pwd, 'data/shapefile.zip')))

        self.media_root = tempfile.mkdtemp()

        with self.settings(MEDIA_ROOT=self.media_root):
            # Create raster layer
            self.rasterlayer = RasterLayer.objects.create(
                name='Raster data',
                description='Small raster for testing',
                datatype='ca',
                nodata='0',
                rasterfile=rasterfile
            )
            self.empty_rasterlayer = RasterLayer.objects.create(
                name='Raster data',
                description='Small raster for testing',
                datatype='ca',
                nodata='0',
                rasterfile=rasterfile
            )
            self.empty_rasterlayer.rastertile_set.all().delete()

            # Create aggregation layer
            self.agglayer = AggregationLayer.objects.create(
                name='abc',
                name_column='name',
                shapefile=shapefile
            )
            # Parse aggregation layer
            self.agglayer.parse()

        # Compute expected totals from numpy value count
        self.expected = {}
        for tile in self.rasterlayer.rastertile_set.filter(tilez=11):
            val, counts = numpy.unique(tile.rast.bands[0].data(), return_counts=True)
            for pair in zip(val, counts):
                if str(pair[0]) in self.expected:
                    self.expected[str(pair[0])] += pair[1]
                else:
                    self.expected[str(pair[0])] = pair[1]

    def tearDown(self):
        shutil.rmtree(self.media_root)
