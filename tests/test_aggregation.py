import inspect
import json
import os
import shutil
import tempfile

from django.core.files import File
from django.test import TestCase
from raster.models import RasterLayer
from raster_aggregation.models import AggregationLayer, ValueCountResult


class RasterAggregationTests(TestCase):

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
                srid='3086',
                nodata='0',
                rasterfile=rasterfile
            )
            # Create aggregation layer
            self.agglayer = AggregationLayer.objects.create(
                name='abc',
                name_column='name',
                shapefile=shapefile
            )
            # Parse aggregation layer
            self.agglayer.parse()
        # Compute value counts
        self.agglayer.compute_value_count()

    def tearDown(self):
        shutil.rmtree(self.media_root)

    def test_count_value_count_results(self):
        self.assertEqual(ValueCountResult.objects.all().count(), 2)

    def test_count_values(self):
        results = ValueCountResult.objects.all()
        self.assertEqual(
            json.loads(results[0].value),
            {"0": 46606, "1": 483, "2": 47, "3": 3817, "4": 29783, "8": 1213, "9": 2511}
        )
        self.assertEqual(
            json.loads(results[1].value),
            {"0": 110345, "1": 682, "2": 53, "3": 4002, "4": 31455, "8": 1272, "9": 2787}
        )
