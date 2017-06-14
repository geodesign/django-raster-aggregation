import django_filters

from django.contrib.postgres.fields import HStoreField
from django.contrib.postgres.forms import HStoreField as HStoreFormField
from raster_aggregation.models import ValueCountResult


class HStoreFieldFilter(django_filters.filters.Filter):

    field_class = HStoreFormField


class ValueCountResultFilter(django_filters.FilterSet):

    class Meta:
        model = ValueCountResult
        fields = (
            'aggregationarea', 'formula', 'layer_names',
            'zoom', 'units', 'grouping', 'status',
            'aggregationarea__aggregationlayer',
        )
        filter_overrides = {
            HStoreField: {
                'filter_class': HStoreFieldFilter,
            },
        }
