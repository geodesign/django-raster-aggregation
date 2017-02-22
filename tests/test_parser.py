from .aggregation_testcase import RasterAggregationTestCase


class AggregationAreaParseTests(RasterAggregationTestCase):

    def test_nr_of_aggregation_areas_created(self):
        self.assertEqual(self.agglayer.aggregationarea_set.count(), 2)

    def test_aggregation_area_properties(self):
        self.assertTrue(self.agglayer.aggregationarea_set.get(name='St Petersburg'))
        self.assertTrue(self.agglayer.aggregationarea_set.get(name='Coverall'))

    def test_parse_log_was_written(self):
        self.agglayer.refresh_from_db()
        self.assertTrue(
            'Started parsing Aggregation Layer' in self.agglayer.parse_log
        )
        self.assertTrue(
            'Finished parsing Aggregation Layer' in self.agglayer.parse_log
        )
