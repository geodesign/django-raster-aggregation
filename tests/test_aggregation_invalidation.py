from __future__ import unicode_literals

from raster_aggregation.models import ValueCountResult
from raster_aggregation.tasks import aggregation_layer_parser, compute_value_count_for_aggregation_layer

from .aggregation_testcase import RasterAggregationTestCase


class RasterAggregationInvalidationTests(RasterAggregationTestCase):

    def setUp(self):
        super(RasterAggregationInvalidationTests, self).setUp()

        compute_value_count_for_aggregation_layer(self.agglayer, self.rasterlayer.id, compute_area=False, grouping=self.legend_exp.id)

    def test_invalidation_from_reparsing_agglayer(self):
        self.assertEqual(ValueCountResult.objects.all().count(), 2)
        with self.settings(MEDIA_ROOT=self.media_root):
            aggregation_layer_parser(self.agglayer.id)
        self.assertEqual(ValueCountResult.objects.all().count(), 0)

    def test_invalidation_from_reparsing_rasterlayer(self):
        self.assertEqual(ValueCountResult.objects.all().count(), 2)

        with self.settings(MEDIA_ROOT=self.media_root):
            # Clear parse log to trigger reparsing of rasterlayer
            self.rasterlayer.parsestatus.reset()
            self.rasterlayer.save()

        # Assert that value count results have been deleted
        self.assertEqual(ValueCountResult.objects.all().count(), 0)

    def test_invalidation_changing_legend(self):
        self.assertEqual(ValueCountResult.objects.all().count(), 2)
        self.legend_exp.save()
        self.assertEqual(ValueCountResult.objects.all().count(), 0)
