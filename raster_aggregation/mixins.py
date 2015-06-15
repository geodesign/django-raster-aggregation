"""
Model method mixins for aggregation models. Contains shapefile data parser and
aggregation results calculator.
"""
import datetime
import json
import os
import shutil
import tempfile
import traceback
import zipfile

from celery.contrib.methods import task

from django.contrib.gis.gdal import CoordTransform, DataSource, SpatialReference
from raster.models import RasterLayer
from raster_aggregation.utils import convert_to_multipolygon


class AggregationDataParser(object):

    @task()
    def parse(self):
        """
        This method pushes the shapefile data from the AggregationLayer
        into the AggregationArea table.
        """
        # Clean previous parse log
        bar = '\n----------------------------------\n'
        now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))
        self.parse_log += bar + now + 'Started parsing Aggregation Layer\n'
        self.save()

        tmpdir = tempfile.mkdtemp()

        shapefilename = os.path.basename(self.shapefile.name)

        shapefilepath = os.path.join(tmpdir, shapefilename)

        # Get zipped shapefile from S3
        try:
            # Access shapefile and store locally
            shapefile = open(shapefilepath, 'wb')
            for chunk in self.shapefile.chunks():
                shapefile.write(chunk)
            shapefile.close()
        except:
            self.parse_log += 'Error: Could not download file, aborted parsing'
            self.save()
            return

        # Open and extract zipfile
        try:
            zf = zipfile.ZipFile(shapefilepath)
            zf.extractall(tmpdir)
        except:
            shutil.rmtree(tmpdir)
            self.parse_log += 'Error: Could not open zipfile, aborted parsing'
            self.save()
            return

        # Remove zipfile
        os.remove(shapefilepath)

        # Set shapefile as datasource for GDAL and get layer
        try:
            ds = DataSource(tmpdir)
            lyr = ds[0]
        except:
            shutil.rmtree(tmpdir)
            self.parse_log += 'Error: Failed to extract layer from shapefile, aborted parsing'
            self.save()
            return

        # Check if name column exists
        if self.name_column not in lyr.fields:
            self.parse_log += 'Error: Name column "{0}" not found, aborted'\
                              ' parsing. Available columns: {1}'.format(self.name_column, lyr.fields)
            self.save()
            return

        # Setup transformation to default ref system
        try:
            ct = CoordTransform(lyr.srs, SpatialReference('WGS84'))
        except:
            shutil.rmtree(tmpdir)
            self.parse_log += 'Error: Layer srs not specified, aborted parsing'
            self.save()
            return

        # Remove existing patches before re-creating them
        self.aggregationarea_set.all().delete()

        # Loop through features
        for feat in lyr:
            # Get geometry and transform to WGS84
            try:
                wgsgeom = feat.geom
                wgsgeom.transform(ct)
            except:
                self.parse_log += 'Warning: Failed to transform feature fid {0}\n'.format(feat.fid)
                continue

            try:
                # Ignore z-dim
                wgsgeom.coord_dim = 2

                # Assure that feature is a valid multipolygon
                this_geom = convert_to_multipolygon(wgsgeom.geos)
            except:
                self.parse_log += 'Warning: Failed to convert feature fid {0} to'\
                                  ' multipolygon\n'.format(feat.fid)
                continue

            # Add warning if geom is not valid
            if wgsgeom.geos.valid_reason != 'Valid Geometry':
                self.parse_log += 'Warning: Found invalid geometry for'\
                                  ' feature fid {0}\n'.format(feat.fid)
                continue

            # If geom is empty, conversion was not successful, issue
            # warning and continue
            if this_geom.empty:
                self.parse_log += 'Warning: Failed to convert feature fid'\
                                  ' {0} to valid geometry\n'.format(feat.fid)
                continue

            # Create aggregation area
            try:
                self.aggregationarea_set.create(
                    name=feat.get(self.name_column),
                    aggregationlayer=self,
                    geom=this_geom
                )
            except:
                self.parse_log += 'Warning: Failed to create AggregationArea'\
                                  'for feature fid {0}\n'.format(feat.fid)

        # Add finish message to parse log
        now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))
        self.parse_log += now + 'Finished parsing shapefile\n'
        self.save()

        # Remove tempdir with unzipped shapefile
        shutil.rmtree(tmpdir)

    @task()
    def compute_value_count(self, simplified=True):
        """Precomputes value counts for all existing rasterlayers"""
        from aggregation.models import ValueCountResult

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
