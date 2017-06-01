import json
import sys
from unittest import skipIf

import mapbox_vector_tile
from raster.tiles.const import WEB_MERCATOR_SRID
from raster.tiles.utils import tile_bounds

from django.contrib.gis.gdal import OGRGeometry
from django.core.urlresolvers import reverse
from django.test import Client
from raster_aggregation.models import AggregationLayerGroup, AggregationLayerZoomRange

from .aggregation_testcase import RasterAggregationTestCase


@skipIf(sys.version_info[:2] == (3, 5), 'The geos version on the CI build breaks this test for Py3.5')
class VectorTilesTests(RasterAggregationTestCase):

    def setUp(self):
        # Run parent setup
        super(VectorTilesTests, self).setUp()

        self.group = AggregationLayerGroup.objects.create(name='Test group')
        AggregationLayerZoomRange.objects.create(
            aggregationlayergroup=self.group,
            aggregationlayer=self.agglayer,
            max_zoom=12,
            min_zoom=3
        )
        # Instantiate test client
        self.client = Client()

    def test_vector_tile_endpoint_json(self):
        # Get url for a tile.
        self.url = reverse('vector_tiles', kwargs={'layergroup': self.group.id, 'z': 11, 'x': 552, 'y': 859, 'response_format': '.json'})
        # Setup request with fromula that will multiply the rasterlayer by itself
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        bounds = tile_bounds(552, 859, 11)
        bounds = OGRGeometry.from_bbox(bounds)
        bounds.srid = WEB_MERCATOR_SRID
        result = json.loads(response.content.decode())
        self.assertEqual(
            'St Petersburg',
            result['features'][0]['properties']['name'],
        )
        self.assertEqual(
            'Coverall',
            result['features'][1]['properties']['name'],
        )

    def test_vector_tile_endpoint_pbf(self):
        # Get url for a tile.
        self.url = reverse('vector_tiles', kwargs={'layergroup': self.group.id, 'z': 11, 'x': 552, 'y': 859, 'response_format': '.pbf'})
        # Setup request with fromula that will multiply the rasterlayer by itself
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        result = mapbox_vector_tile.decode(response.content)
        self.assertEqual(
            'St Petersburg',
            result['testlayer']['features'][0]['properties']['name'],
        )
        self.assertEqual(
            'Coverall',
            result['testlayer']['features'][1]['properties']['name'],
        )

    def test_vector_tile_wrong_format(self):
        # Get url for a tile, switch to an invalid format.
        self.url = reverse('vector_tiles', kwargs={'layergroup': self.group.id, 'z': 11, 'x': 552, 'y': 859, 'response_format': '.json'})
        self.url = self.url.split('.json')[0] + '.doc'
        # Setup request with fromula that will multiply the rasterlayer by itself
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)
        self.assertTrue('The requested URL /vtiles/3/11/552/859.doc was not found on this server.' in response.content.decode())
