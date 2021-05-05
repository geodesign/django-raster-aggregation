import json

import mapbox_vector_tile
from raster.tiles.const import WEB_MERCATOR_SRID
from raster.tiles.utils import tile_bounds

from django.contrib.gis.gdal import OGRGeometry
from django.urls import reverse

from .aggregation_testcase import RasterAggregationTestCase


class VectorTilesTests(RasterAggregationTestCase):

    def test_vector_tile_endpoint_json(self):
        # Get url for a tile.
        self.url = reverse('vectortiles-list', kwargs={'aggregationlayer': self.agglayer.id, 'z': 11, 'x': 552, 'y': 859, 'frmt': 'json'})
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
        self.assertEqual(
            [-9220428.84343788, 3228174.36658215],
            result['features'][0]['geometry']['coordinates'][0][0][0],
        )

    def test_vector_tile_endpoint_pbf(self):
        # Get url for a tile.
        self.url = reverse('vectortiles-list', kwargs={'aggregationlayer': self.agglayer.id, 'z': 11, 'x': 552, 'y': 859, 'frmt': 'pbf'})
        # Setup request with fromula that will multiply the rasterlayer by itself
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        result = mapbox_vector_tile.decode(response.content)
        self.assertEqual(
            'St Petersburg',
            result['My Aggregation Layer']['features'][0]['properties']['name'],
        )
        self.assertEqual(
            'Coverall',
            result['My Aggregation Layer']['features'][1]['properties']['name'],
        )
        self.assertEqual(
            'An area that covers everything.',
            result['My Aggregation Layer']['features'][1]['properties']['LongName'],
        )
        self.assertEqual(
            [3268, 3986],
            result['My Aggregation Layer']['features'][0]['geometry']['coordinates'][0][0][0],
        )

    def test_vector_tile_wrong_format(self):
        # Get url for a tile, switch to an invalid format.
        self.url = reverse('vectortiles-list', kwargs={'aggregationlayer': self.agglayer.id, 'z': 11, 'x': 552, 'y': 859, 'frmt': 'json'})
        self.url = self.url.split('.json')[0] + '.doc'
        # Setup request with fromula that will multiply the rasterlayer by itself
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)
