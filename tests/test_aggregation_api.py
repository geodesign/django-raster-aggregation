from __future__ import unicode_literals

import json

from raster.models import RasterLayer

from django.core.urlresolvers import reverse_lazy as reverse
from django.test import Client
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
        self.url = reverse('valuecountresult-list')

        self.data = {
            'aggregationarea': self.area.id,
            'layer_names': {'a': self.rasterlayer.id, 'b': self.rasterlayer.id},
            'formula': 'a*b',
        }

    def _create_obj(self):
        #  Create object through api.
        response = self.client.post(self.url, json.dumps(self.data), format='json', content_type='application/json')
        self.assertEqual(response.status_code, 201)
        result = json.loads(response.content.strip().decode())
        # Async result has not been created, but scheduled.
        self.assertEqual(result['value'], {})
        self.assertEqual(result['status'], 'Scheduled')

        # Get detail view to obtain value count result.
        url = reverse('valuecountresult-detail', kwargs={'pk': result['id']})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.strip().decode())
        # Assert result has the right aggregationarea id
        self.assertEqual(result['aggregationarea'], self.area.id)
        return result

    def test_aggregation_api_count(self):
        result = self._create_obj()

        # Compute expected values (same counts, but squared keys due to formula)
        expected = {str(int(k) ** 2): v for k, v in self.expected.items()}

        # Assert all data values are according to the formula
        self.assertDictEqual(result['value'], expected)

    def test_aggregation_api_count_explicit_zoom(self):
        self.data['zoom'] = 11
        result = self._create_obj()

        # Compute expected values (same counts, but squared keys due to formula)
        expected = {str(int(k) ** 2): v for k, v in self.expected.items()}

        self.assertDictEqual(result['value'], expected)

    def test_aggregation_api_areas(self):
        #  Create object through api.
        self.data['units'] = 'acres'
        result = self._create_obj()

        # Simplify result to integers (ignore rounding differences).
        result = {k: round(float(v)) for k, v in result['value'].items()}

        # Compute the expected result (squaring the value of each pixel), scaling counts to acres
        expected = {str(int(k) ** 2): round(v * 1.4437426664517252) for k, v in self.expected.items()}

        # Assert all data values are according to the formula
        self.assertDictEqual(result, expected)

    def test_aggregation_api_legend_expression_grouping(self):
        #  Create object through api.
        self.data['grouping'] = self.legend_exp.id
        self.data['formula'] = 'a'
        result = self._create_obj()

        expected = {'(x >= 2) & (x < 5)': self.expected['2'] + self.expected['3'] + self.expected['4']}

        # Assert all data values are according to the formula
        self.assertDictEqual(result['value'], expected)

    def test_aggregation_api_legend_float_grouping(self):
        #  Create object through api.
        self.data['grouping'] = self.legend_float.id
        self.data['formula'] = 'a'
        result = self._create_obj()

        expected = {'2': self.expected['2'], '4': self.expected['4']}

        # Assert all data values are according to the formula
        self.assertDictEqual(result['value'], expected)

    def test_aggregation_api_json_grouping(self):
        #  Create object through api.
        self.data['grouping'] = self.legend_exp.json
        self.data['formula'] = 'a'
        result = self._create_obj()

        expected = {'(x >= 2) & (x < 5)': self.expected['2'] + self.expected['3'] + self.expected['4']}

        # Assert all data values are according to the formula
        self.assertDictEqual(result['value'], expected)

    def test_value_count_for_raster_with_missing_tile(self):
        self.data['layer_names'] = {'a': self.rasterlayer.id, 'b': self.empty_rasterlayer.id}
        result = self._create_obj()

        # Assert all data values are empty
        self.assertEqual(result['value'], {})

    def test_filter_by_layer(self):
        self._create_obj()

        # Valuecountresult filtering.
        url = reverse('valuecountresult-list')

        response = self.client.get(url + '?aggregationarea__aggregationlayer={0}'.format(self.agglayer.id))
        result = json.loads(response.content.strip().decode())

        count = len(result)
        self.assertTrue(count > 0)
        self.assertEqual(count, ValueCountResult.objects.filter(aggregationarea=self.area).count())

        response = self.client.get(url + '?aggregationarea__aggregationlayer=1234')  # Not existing agglayer id.
        count = len(json.loads(response.content.strip().decode()))
        self.assertEqual(0, count)

        # Aggregationarea filtering.
        url = reverse('aggregationarea-list')
        response = self.client.get(url + '?aggregationlayer={0}'.format(self.agglayer.id))
        result = json.loads(response.content.strip().decode())

        count = len(result)
        self.assertTrue(count > 0)
        self.assertEqual(count, AggregationArea.objects.filter(aggregationlayer=self.agglayer).count())

        response = self.client.get(url + '?aggregationlayer=1234')  # Not existing agglayer id.
        count = len(json.loads(response.content.strip().decode()))
        self.assertEqual(0, count)

    def test_aggregation_null_values(self):
        self.data['formula'] = '99*(a==NULL)+2*(~a==2)'
        result = self._create_obj()['value']

        self.data['formula'] = '99*(~a==0)'
        result2 = self._create_obj()['value']

        # Assert all data values are according to the formula
        self.assertEqual(self.expected['2'], result['2'])
        self.assertEqual(result['99'], result2['99'])
        self.assertTrue(result['99'] > 0)

    def test_aggregation_api_count_maxzoom_parameter(self):
        self.url += '?maxzoom=3'
        result = self._create_obj()

        # Value count was bounded by given zoom level
        self.assertEqual(result['zoom'], 3)

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

        self.url += '?minmaxzoom'
        self.data['layer_names'] = {'a': self.rasterlayer.id, 'b': rasterlayer_low_res.id}
        result = self._create_obj()

        # Value count was bounded by given zoom level
        self.assertEqual(result['zoom'], 3)

    def test_aggregation_api_unique_constraint(self):
        self._create_obj()
        response = self.client.post(self.url, json.dumps(self.data), format='json', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b'{"detail":"A value count object with this properties already exists."}')
