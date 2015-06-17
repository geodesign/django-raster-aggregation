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
        shapefile = File(open(os.path.join(self.pwd, 'data/polygon.zip')))

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
            self.agglayer.parse()

    def tearDown(self):
        shutil.rmtree(self.media_root)

    def test_agg(self):
        # Compute value count
        self.agglayer.compute_value_count()
        # Get valuecount result
        results = ValueCountResult.objects.all()
        self.assertEqual(results.count(), 1)
        self.assertEqual(
            json.loads(results.first().value),
            {"0": 46427, "1": 481, "2": 47, "3": 3797, "4": 29629, "8": 1208, "9": 2505}
        )
