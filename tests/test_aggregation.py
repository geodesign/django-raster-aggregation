import inspect
import json
import os
import shutil
import tempfile

import numpy

from django.core.files import File
from django.test import TestCase
from raster.models import RasterLayer
from raster_aggregation.models import AggregationArea, AggregationLayer, ValueCountResult


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
        self.agglayer.compute_value_count(self.rasterlayer.id)

    def tearDown(self):
        shutil.rmtree(self.media_root)

    def test_count_value_count_results(self):
        self.assertEqual(ValueCountResult.objects.all().count(), 2)

    def test_count_values_for_st_petersburg(self):
        result = ValueCountResult.objects.get(aggregationarea__name='St Petersburg')
        self.assertEqual(
            json.loads(result.value),
            {"0": 50036, "1": 536, "2": 53, "3": 4044, "4": 31134, "8": 1214, "9": 2674}
        )

    def test_count_values_for_coverall(self):
        # Get result
        result = ValueCountResult.objects.get(aggregationarea__name='Coverall')
        result = json.loads(result.value)
        # Compute expected totals from numpy value count
        expected = {}
        for tile in self.rasterlayer.rastertile_set.filter(tilez=11):
            val, counts = numpy.unique(tile.rast.bands[0].data(), return_counts=True)
            for pair in zip(val, counts):
                if str(pair[0]) in expected:
                    expected[str(pair[0])] += pair[1]
                else:
                    expected[str(pair[0])] = pair[1]
        # Assert totals are correct
        self.assertEqual(
            sum(result.values()),
            sum(expected.values()) + (111138 - expected["0"])
        )
        # Remove nodata value - the tiles are not entirely
        # covered by the coverall geom.
        expected.pop("0")
        # Assert the nodata value is as expected
        self.assertEqual(result.pop("0"), 111138)
        # Assert value counts are correct
        self.assertEqual(result, expected)

    def test_get_result_method_for_st_petersburg(self):
        area = AggregationArea.objects.get(name='St Petersburg')
        self.assertEqual(
            area.get_value_count(self.rasterlayer.id),
            {"0": 50036, "1": 536, "2": 53, "3": 4044, "4": 31134, "8": 1214, "9": 2674}
        )
