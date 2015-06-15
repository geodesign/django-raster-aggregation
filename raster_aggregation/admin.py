"""Admin registry for aggregation app"""

from django.contrib import admin
from wsc.utils.adminutils import ParseShapefileModelAdmin

from .models import AggregationArea, AggregationLayer, ValueCountResult


class ValueCountResultAdmin(admin.ModelAdmin):
    readonly_fields = ('rasterlayer', 'aggregationarea', 'value')


class ComputeActivityAggregatesModelAdmin(ParseShapefileModelAdmin):

    actions = ['parse_shapefile_data', 'compute_value_count', 'compute_value_count_simplified']

    def compute_value_count(self, request, queryset):
        # Send parse data command to celery
        for lyr in queryset:
            lyr.compute_value_count.delay(simplified=False)

        # Message user
        self.message_user(request,
            "Computing aggregates asynchronously, please check the parse log for status(es)")

    def compute_value_count_simplified(self, request, queryset):
        # Send parse data command to celery
        for lyr in queryset:
            lyr.compute_value_count.delay(simplified=True)

        # Message user
        self.message_user(request,
            "Computing aggregates asynchronously, please check the parse log for status(es)")

admin.site.register(AggregationArea)
admin.site.register(ValueCountResult, ValueCountResultAdmin)
admin.site.register(AggregationLayer, ComputeActivityAggregatesModelAdmin)
