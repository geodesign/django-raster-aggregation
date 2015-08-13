import inspect
import json
import os
import shutil
import tempfile
from collections import OrderedDict

import numpy

from django.core.files import File
from django.core.urlresolvers import reverse
from django.test import Client, TestCase
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
        self.agglayer.compute_value_count(self.rasterlayer.id, compute_area=False)

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

    def test_count_value_count_results(self):
        self.assertEqual(ValueCountResult.objects.all().count(), 2)

    def test_count_values_for_st_petersburg(self):
        result = ValueCountResult.objects.get(aggregationarea__name='St Petersburg')
        self.assertEqual(
            json.loads(result.value),
            {'0': 49949, '1': 545, '2': 56, '3': 4094, '4': 30970, '8': 1260, '9': 2817}
        )

    def test_count_values_for_coverall(self):
        # Get result
        result = ValueCountResult.objects.get(aggregationarea__name='Coverall')
        result = json.loads(result.value)
        # Assert totals are correct
        self.assertEqual(
            sum(result.values()),
            sum(self.expected.values()) + (111049 - self.expected["0"])
        )
        # Remove nodata value - the tiles are not entirely
        # covered by the coverall geom.
        self.expected.pop("0")
        # Assert the nodata value is as expected
        self.assertEqual(result.pop("0"), 111049)
        # Assert value counts are correct
        self.assertEqual(result, self.expected)

    def test_get_result_method_for_st_petersburg(self):
        area = AggregationArea.objects.get(name='St Petersburg')
        self.assertEqual(
            area.get_value_count(self.rasterlayer.id),
            {'0': 49949, '1': 545, '2': 56, '3': 4094, '4': 30970, '8': 1260, '9': 2817}
        )

    def test_aggregation_url(self):
        area = AggregationArea.objects.get(name='Coverall')
        # Instantiate test client
        self.client = Client()
        url = reverse('aggregate', kwargs={'area': area.id})

        # Setup request with fromula that will multiply the rasterlayer by itself
        response = self.client.get(url + '?layers=a={0},b={0}&formula=a*b&zoom=11'.format(self.rasterlayer.id))
        self.assertEqual(response.status_code, 200)

        # Compute the expected result (squaring the value of each pixel)
        expected = OrderedDict({str(int(k) ** 2): v for k, v in self.expected.items()})

        # Order results
        result = OrderedDict(json.loads(response.content))

        # Pop the nodata value (this is the part that gets clipped by the coverall geom
        result.pop('0')
        expected.pop('0')

        # Assert all data values are according to the formula
        self.assertEqual(result, expected)
