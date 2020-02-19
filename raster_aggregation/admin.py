from __future__ import unicode_literals

from raster.models import RasterLayer

from django import forms
from django.contrib.gis import admin
from django.http import HttpResponseRedirect
from django.shortcuts import render

from .models import AggregationArea, AggregationLayer, AggregationLayerGroup, ValueCountResult
from .tasks import aggregation_layer_parser, compute_value_count_for_aggregation_layer


class ValueCountResultAdmin(admin.ModelAdmin):
    readonly_fields = (
        'aggregationarea', 'rasterlayers', 'formula',
        'layer_names', 'zoom', 'units', 'value', 'created'
    )


class SelectLayerActionForm(forms.Form):
    """
    Form for selecting the raster-layer on which to compute value counts.
    """
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    rasterlayers = forms.ModelMultipleChoiceField(queryset=RasterLayer.objects.all(), required=True)


class ComputeActivityAggregatesModelAdmin(admin.ModelAdmin):

    readonly_fields = ['modified']

    actions = ['parse_shapefile_data', 'compute_value_count', ]

    search_fields = ('name', )

    def parse_shapefile_data(self, request, queryset):
        for lyr in queryset.all():
            lyr.log('Scheduled shapefile parsing.', AggregationLayer.PENDING)
            aggregation_layer_parser.delay(lyr.id)
            self.message_user(
                request,
                "Parsing shapefile asynchronously, please check the collection parse log for status.",
            )

    def compute_value_count(self, request, queryset):

        form = None
        layer = queryset[0]

        # After posting, set the new name to file field
        if 'apply' in request.POST:
            form = SelectLayerActionForm(request.POST)

            if form.is_valid():
                rasterlayers = form.cleaned_data['rasterlayers']

                for rst in rasterlayers:
                    compute_value_count_for_aggregation_layer(
                        layer,
                        rst.id,
                        compute_area=True
                    )

                self.message_user(
                    request,
                    "Started Value Count on \"{agg}\" with {count} rasters. "
                    "Check parse log for results.".format(agg=layer, count=rasterlayers.count())
                )
                return HttpResponseRedirect(request.get_full_path())

        # Before posting, prepare empty action form
        if not form:
            form = SelectLayerActionForm(initial={
                '_selected_action': request.POST.getlist(admin.ACTION_CHECKBOX_NAME),
            })

        return render(
            request,
            'raster_aggregation/select_raster_for_aggregation.html',
            {
                'layers': RasterLayer.objects.all(),
                'form': form,
                'title': u'Select Layer on which to Compute Value Counts'
            }
        )


class AggregationLayerInLine(admin.TabularInline):
    model = AggregationLayerGroup.aggregationlayers.through


class AggregationLayerGroupAdmin(admin.ModelAdmin):
    inlines = (
        AggregationLayerInLine,
    )
    exclude = ['aggregationlayers']


class AggregationAreaAdmin(admin.OSMGeoAdmin):
    raw_id_fields = ('aggregationlayer', )
    search_fields = ('name', )


admin.site.register(AggregationArea, AggregationAreaAdmin)
admin.site.register(ValueCountResult, ValueCountResultAdmin)
admin.site.register(AggregationLayer, ComputeActivityAggregatesModelAdmin)
admin.site.register(AggregationLayerGroup, AggregationLayerGroupAdmin)
