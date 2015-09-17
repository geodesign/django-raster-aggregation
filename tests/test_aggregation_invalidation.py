from raster_aggregation.models import ValueCountResult
from raster_aggregation.tasks import compute_value_count_for_aggregation_layer

from .aggregation_testcase import RasterAggregationTestCase


class RasterAggregationInvalidationTests(RasterAggregationTestCase):

    def setUp(self):
        super(RasterAggregationInvalidationTests, self).setUp()

        compute_value_count_for_aggregation_layer(self.agglayer, self.rasterlayer.id, compute_area=False)

    def test_invalidation_from_reparsing_agglayer(self):
        self.assertEqual(ValueCountResult.objects.all().count(), 2)
        self.agglayer.parse()
        self.assertEqual(ValueCountResult.objects.all().count(), 0)

    def test_invalidation_from_reparsing_rasterlayer(self):
        self.assertEqual(ValueCountResult.objects.all().count(), 2)

        # Clear parse log to trigger reparsing of rasterlayer
        self.rasterlayer.parse_log = ''
        self.rasterlayer.save()

        # Assert that value count results have been deleted
        self.assertEqual(ValueCountResult.objects.all().count(), 0)
