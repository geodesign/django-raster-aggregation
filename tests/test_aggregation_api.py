import json

from raster.models import RasterLayer

from django.core.urlresolvers import reverse_lazy as reverse
from django.test import Client
from django.utils.http import urlquote
from raster_aggregation.models import AggregationArea, ValueCountResult

from .aggregation_testcase import RasterAggregationTestCase


class RasterAggregationApiTests(RasterAggregationTestCase):

    def setUp(self):
        # Run parent setup
        super(RasterAggregationApiTests, self).setUp()

        # Get aggregation area to compute aggregation
        self.area = AggregationArea.objects.get(name='Coverall')

        # Assert value count result does not yet exist
        self.assertFalse(ValueCountResult.objects.filter(aggregationarea=self.area).exists())

        # Instantiate test client
        self.client = Client()

        # Get api url for the given aggregation area
        self.url = reverse('aggregationareavalue-detail', kwargs={'pk': self.area.id})

    def test_aggregation_api_count(self):
        # Setup request with fromula that will multiply the rasterlayer by itself
        response = self.client.get(self.url + '?layers=a={0},b={0}&formula=a*b&zoom=11'.format(self.rasterlayer.id))
        self.assertEqual(response.status_code, 200)

        # Assert result has the right aggregationarea id
        self.assertEqual(json.loads(response.content.strip().decode())['id'], self.area.id)

        # Load results into ordered dict
        result = json.loads(response.content.strip().decode())['value']

        # Compute expected values (same counts, but squared keys due to formula)
        expected = {str(int(k) ** 2): v for k, v in self.expected.items()}

        # Assert all data values are according to the formula
        self.assertDictEqual(result, expected)

        # Assert value count result was created
        self.assertTrue(ValueCountResult.objects.filter(aggregationarea=self.area).exists())

    def test_aggregation_api_areas(self):
        # Request result
        response = self.client.get(self.url + '?layers=a={0},b={0}&formula=a*b&acres'.format(self.rasterlayer.id))
        self.assertEqual(response.status_code, 200)

        # Assert result has the right aggregationarea id
        self.assertEqual(json.loads(response.content.strip().decode())['id'], self.area.id)

        # Parse result
        result = json.loads(response.content.strip().decode())['value']
        result = {k: round(float(v)) for k, v in result.items()}

        # Compute the expected result (squaring the value of each pixel), scaling counts to acres
        expected = {str(int(k) ** 2): round(v * 1.4437426664517252) for k, v in self.expected.items()}

        # Assert all data values are according to the formula
        self.assertDictEqual(result, expected)

        # Assert value count result was created
        self.assertTrue(ValueCountResult.objects.filter(aggregationarea=self.area).exists())

    def test_aggregation_api_legend_expression_grouping(self):
        # Request result
        response = self.client.get(
            self.url + '?layers=a={0}&formula=a&grouping={1}'
            .format(self.rasterlayer.id, self.legend_exp.id)
        )
        self.assertEqual(response.status_code, 200)

        # Assert result has the right aggregationarea id
        self.assertEqual(json.loads(response.content.strip().decode())['id'], self.area.id)

        # Parse result
        result = json.loads(response.content.strip().decode())['value']

        expected = {'(x >= 2) & (x < 5)': self.expected['2'] + self.expected['3'] + self.expected['4']}

        # Assert all data values are according to the formula
        self.assertDictEqual(result, expected)

        # Assert value count result was created
        self.assertTrue(ValueCountResult.objects.filter(aggregationarea=self.area).exists())

    def test_aggregation_api_legend_float_grouping(self):
        # Request result
        response = self.client.get(
            self.url + '?layers=a={0}&formula=a&grouping={1}'
            .format(self.rasterlayer.id, self.legend_float.id)
        )
        self.assertEqual(response.status_code, 200)

        # Assert result has the right aggregationarea id
        self.assertEqual(json.loads(response.content.strip().decode())['id'], self.area.id)

        # Parse result
        result = json.loads(response.content.strip().decode())['value']

        expected = {'2': self.expected['2'], '4': self.expected['4']}

        # Assert all data values are according to the formula
        self.assertDictEqual(result, expected)

        # Assert value count result was created
        self.assertTrue(ValueCountResult.objects.filter(aggregationarea=self.area).exists())

    def test_aggregation_api_json_grouping(self):
        # Request result
        response = self.client.get(
            self.url + '?layers=a={0}&formula=a&grouping={1}'
            .format(self.rasterlayer.id, urlquote(self.legend_exp.json))
        )
        self.assertEqual(response.status_code, 200)

        # Assert result has the right aggregationarea id
        self.assertEqual(json.loads(response.content.strip().decode())['id'], self.area.id)

        # Parse result
        result = json.loads(response.content.strip().decode())['value']

        expected = {'(x >= 2) & (x < 5)': self.expected['2'] + self.expected['3'] + self.expected['4']}

        # Assert all data values are according to the formula
        self.assertDictEqual(result, expected)

    def test_value_count_for_raster_with_missing_tile(self):
        url = reverse('aggregationareavalue-list')

        # Setup request with fromula that will multiply the rasterlayer by itself
        response = self.client.get(url + '?layers=a={0},b={1}&formula=a*b&zoom=4'.format(self.rasterlayer.id, self.empty_rasterlayer.id))

        # Parse result values
        result = [dat['value'] for dat in json.loads(response.content.strip().decode())]

        # Assert all data values are empty
        self.assertEqual(result, [{}, {}])

    def test_filter_by_layer(self):
        url = reverse('aggregationareavalue-list')

        # Setup request with fromula that will multiply the rasterlayer by itself
        response = self.client.get(url + '?layers=a={0}&formula=a&zoom=4&aggregationlayer={1}'.format(
            self.rasterlayer.id,
            self.agglayer.id,
        ))

        count = len(json.loads(response.content.strip().decode()))
        self.assertEqual(count, self.agglayer.aggregationarea_set.count())

        response = self.client.get(url + '?layers=a={0}&formula=a&zoom=4&aggregationlayer={1}'.format(
            self.rasterlayer.id,
            1234,  # Not existing agglayer id.
        ))
        count = len(json.loads(response.content.strip().decode()))
        self.assertEqual(0, count)

    def test_aggregation_null_values(self):
        response = self.client.get(
            self.url + '?layers=a={0}&formula=99*(a==NULL)%2B2*(~a==2)'.format(self.rasterlayer.id)
        )
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.strip().decode())['value']

        response = self.client.get(
            self.url + '?layers=a={0}&formula=99*(~a==0)'.format(self.rasterlayer.id)
        )
        self.assertEqual(response.status_code, 200)
        result2 = json.loads(response.content.strip().decode())['value']

        # Assert all data values are according to the formula
        self.assertEqual(self.expected['2'], result['2'])
        self.assertEqual(result['99'], result2['99'])
        self.assertTrue(result['99'] > 0)

    def test_aggregation_api_count_maxzoom_parameter(self):
        # Setup request with fromula that will multiply the rasterlayer by itself
        response = self.client.get(self.url + '?layers=a={0},b={0}&formula=a*b&maxzoom=3'.format(self.rasterlayer.id))
        self.assertEqual(response.status_code, 200)

        # Assert result has the right aggregationarea id
        self.assertEqual(json.loads(response.content.strip().decode())['id'], self.area.id)

        # Value count was bounded by given zoom level
        self.assertEqual(
            ValueCountResult.objects.filter(aggregationarea=self.area).first().zoom,
            3
        )

    def test_aggregation_api_count_minmaxzoom_parameter(self):
        # Create another rasterlayer with low max_zoom value.
        with self.settings(MEDIA_ROOT=self.media_root):
            rasterlayer_low_res = RasterLayer.objects.create(
                name='Raster data',
                description='Second small raster for testing',
                datatype='ca',
                nodata=0,
                max_zoom=3,
                rasterfile=self.rasterfile
            )
        # Setup request with fromula that will multiply the rasterlayer by itself
        response = self.client.get(self.url + '?layers=a={0},b={1}&formula=a*b&minmaxzoom'.format(self.rasterlayer.id, rasterlayer_low_res.id))
        self.assertEqual(response.status_code, 200)

        # Assert result has the right aggregationarea id
        self.assertEqual(json.loads(response.content.strip().decode())['id'], self.area.id)

        # Value count was bounded by given zoom level
        self.assertEqual(
            ValueCountResult.objects.filter(aggregationarea=self.area).first().zoom,
            3
        )
