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
            {'--': 49949, '1': 545, '2': 56, '3': 4094, '4': 30970, '8': 1260, '9': 2817}
        )

    def test_count_values_for_coverall(self):
        # Get result
        result = ValueCountResult.objects.get(aggregationarea__name='Coverall')
        result = {k: float(v) for k, v in result.value.items()}

        # Assert totals are correct
        self.assertEqual(
            sum(result.values()),
            sum(self.expected.values()) + (111049 - self.expected["0"])
        )
        # Remove nodata value - the tiles are not entirely
        # covered by the coverall geom.
        self.expected.pop("0")
        # Assert the nodata value is as expected
        self.assertEqual(result.pop("--"), 111049)
        # Assert value counts are correct
        self.assertEqual(result, self.expected)
