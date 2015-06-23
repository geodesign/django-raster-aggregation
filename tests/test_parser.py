import inspect
import os
import shutil
import tempfile

from django.core.files import File
from django.test import TestCase
from raster_aggregation.models import AggregationLayer


class AggregationAreaParseTests(TestCase):

    def setUp(self):
        # Instantiate Django file instances with nodes and links
        self.pwd = os.path.dirname(
            os.path.abspath(
                inspect.getfile(inspect.currentframe())
            )
        )

        shapefile = File(open(os.path.join(self.pwd, 'data/shapefile.zip')))

        self.media_root = tempfile.mkdtemp()

        with self.settings(MEDIA_ROOT=self.media_root):

            # Create aggregation layer
            self.agglayer = AggregationLayer.objects.create(
                name='abc',
                name_column='name',
                shapefile=shapefile
            )
            # Parse aggregation layer
            self.agglayer.parse()

    def tearDown(self):
        shutil.rmtree(self.media_root)

    def test_nr_of_aggregation_areas_created(self):
        self.assertEqual(self.agglayer.aggregationarea_set.count(), 2)

    def test_aggregation_area_properties(self):
        self.assertTrue(self.agglayer.aggregationarea_set.get(name='St Petersburg'))
        self.assertTrue(self.agglayer.aggregationarea_set.get(name='Coverall'))

    def test_parse_log_was_written(self):
        self.assertTrue(
            'Started parsing Aggregation Layer' in self.agglayer.parse_log
        )
        self.assertTrue(
            'Finished parsing Aggregation Layer' in self.agglayer.parse_log
        )
