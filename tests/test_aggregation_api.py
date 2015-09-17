import json

from django.core.urlresolvers import reverse
from django.test import Client
from raster_aggregation.models import AggregationArea, ValueCountResult

from .aggregation_testcase import RasterAggregationTestCase


class RasterAggregationApiTests(RasterAggregationTestCase):

    def test_aggregation_api_count(self):
        # Get aggregation area to compute aggregation
        area = AggregationArea.objects.get(name='Coverall')

        # Assert value count result does not yet exist
        self.assertFalse(ValueCountResult.objects.filter(aggregationarea=area).exists())

        # Instantiate test client
        self.client = Client()

        # Get api url for the given aggregation area
        url = reverse('aggregationareavalue-detail', kwargs={'pk': area.id})

        # Setup request with fromula that will multiply the rasterlayer by itself
        response = self.client.get(url + '?layers=a={0},b={0}&formula=a*b&zoom=11'.format(self.rasterlayer.id))
        response_acres = self.client.get(url + '?layers=a={0},b={0}&formula=a*b&zoom=11&acres'.format(self.rasterlayer.id))

        self.assertEqual(response.status_code, 200)

        # Compute the expected result (squaring the value of each pixel)
        expected = {str(int(k) ** 2): v for k, v in self.expected.items()}
        expected_acres = {str(int(k) ** 2): round(v * 1.4437426664517252) for k, v in self.expected.items()}

        # Assert result has the right aggregationarea id
        self.assertEqual(json.loads(response.content)['id'], area.id)

        # Load results into ordered dict
        result = json.loads(response.content)['value']
        result_acres = json.loads(response_acres.content)['value']
        result_acres = {k: round(float(v)) for k, v in result_acres.items()}

        # Pop the nodata value (this is the part that gets clipped by the coverall geom
        result.pop('--')
        result_acres.pop('--')

        expected.pop('0')
        expected_acres.pop('0')

        # Assert all data values are according to the formula
        self.assertDictEqual(result, expected)
        self.assertDictEqual(result_acres, expected_acres)

        # Assert value count result was created
        self.assertTrue(ValueCountResult.objects.filter(aggregationarea=area).exists())
