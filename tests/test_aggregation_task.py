from __future__ import unicode_literals

from raster_aggregation.models import ValueCountResult
from raster_aggregation.tasks import compute_value_count_for_aggregation_layer

from .aggregation_testcase import RasterAggregationTestCase


class RasterAggregationTaskTests(RasterAggregationTestCase):

    def setUp(self):
        super(RasterAggregationTaskTests, self).setUp()

        compute_value_count_for_aggregation_layer(self.agglayer, self.rasterlayer.id, compute_area=False)

    def test_count_value_count_results(self):
        self.assertEqual(ValueCountResult.objects.all().count(), 2)

    def test_count_values_for_st_petersburg(self):
        result = ValueCountResult.objects.get(aggregationarea__name='St Petersburg')
        result = {k: float(v) for k, v in result.value.items()}
        self.assertEqual(
            result,
            {'1': 605, u'15': 747, '2': 56, '3': 4115, '4': 31362, '8': 1284, '9': 2879}
        )

    def test_count_values_for_coverall(self):
        # Get result
        result = ValueCountResult.objects.get(aggregationarea__name='Coverall')
        result = {k: float(v) for k, v in result.value.items()}

        # Assert value counts are correct
        self.assertDictEqual(result, self.expected)

    def test_value_count_results_with_hist_range(self):
        vc = ValueCountResult.objects.get(aggregationarea__name='Coverall')
        self.assertEqual(vc.stats_min, 1)
        self.assertEqual(vc.stats_max, 15)
        self.assertAlmostEqual(vc.stats_avg, 4.65901342)

        vc.range_min = 1.5
        vc.range_max = 8
        vc.populate()
        vc.refresh_from_db()

        self.assertEqual(vc.stats_min, 2)
        self.assertEqual(vc.stats_max, 8)
        self.assertAlmostEqual(vc.stats_avg, 4.03124746)
