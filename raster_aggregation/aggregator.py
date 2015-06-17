import datetime
import json
import traceback

from celery.contrib.methods import task

from raster.models import RasterLayer


class Aggregator(object):

    @task()
    def compute_value_count(self, simplified=True):
        """
        Precomputes value counts for all existing rasterlayers.
        """
        from raster_aggregation.models import ValueCountResult

        # Open parse log
        self.parse_log += '\n ----- Starting Value count ----- \n Computing on {0} Geometries\n'.format(
            'Simplified' if simplified else 'Original')
        self.save()

        for area in self.aggregationarea_set.all():
            # Remove existing results
            area.valuecountresult_set.all().delete()

            now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))
            self.parse_log += now + 'Computing Value Count for area {0}\n'.format(area.id)
            self.save()

            # Create stats for all rasters
            for rast in RasterLayer.objects.filter(datatype='ca'):
                # Get geometry
                if simplified:
                    geom = area.geom_simplified
                else:
                    geom = area.geom
                try:
                    count = rast.value_count(geom)
                    ValueCountResult.objects.create(rasterlayer=rast,
                                                    aggregationarea=area,
                                                    value=json.dumps(count))
                except:
                    self.parse_log += 'ERROR: Failed to compute value count for '\
                                      'area {0} and rast {1}'.format(area.id, rast.id)
                    self.parse_log += traceback.format_exc()
                    self.save()
        # Close parse log
        now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))
        self.parse_log += now + '\n----- Ended Value Count -----\n'
        self.save()
