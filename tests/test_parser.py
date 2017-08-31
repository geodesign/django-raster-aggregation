from __future__ import unicode_literals

from .aggregation_testcase import RasterAggregationTestCase


class AggregationAreaParseTests(RasterAggregationTestCase):

    def test_nr_of_aggregation_areas_created(self):
        self.assertEqual(self.agglayer.aggregationarea_set.count(), 2)

    def test_aggregation_area_properties(self):
        self.assertEqual(
            self.agglayer.aggregationarea_set.get(name='St Petersburg').attributes,
            {'id': '0', 'Name': 'St Petersburg'},
        )
        self.assertEqual(
            self.agglayer.aggregationarea_set.get(name='Coverall').attributes,
            {'id': '1', 'Name': 'Coverall'},
        )

    def test_agglayer_fields_property(self):
        self.agglayer.refresh_from_db()
        self.assertIn(self.agglayer.fields['id'], ('OFTInteger', 'OFTInteger64'))
        self.assertEqual(self.agglayer.fields['Name'], 'OFTString')

    def test_parse_log_was_written(self):
        self.agglayer.refresh_from_db()
        self.assertTrue(
            'Started parsing Aggregation Layer' in self.agglayer.parse_log
        )
        self.assertTrue(
            'Finished parsing Aggregation Layer' in self.agglayer.parse_log
        )
