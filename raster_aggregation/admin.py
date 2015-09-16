from django import forms
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from raster.models import RasterLayer

from .models import AggregationArea, AggregationLayer, ValueCountResult
from .tasks import compute_value_count


class ValueCountResultAdmin(admin.ModelAdmin):
    readonly_fields = ('rasterlayer', 'aggregationarea', 'value')


class SelectLayerActionForm(forms.Form):
    """
    Form for selecting the raster-layer on which to compute value counts.
    """
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    rasterlayers = forms.ModelMultipleChoiceField(queryset=RasterLayer.objects.all(), required=True)
    simplified = forms.BooleanField(label='Use simplified geometries', required=True)


class ComputeActivityAggregatesModelAdmin(admin.ModelAdmin):

    actions = ['parse_shapefile_data', 'compute_value_count', ]

    def parse_shapefile_data(self, request, queryset):
        if queryset.count() > 1:
            self.message_user(request,
                'You can only parse one file at a time, please select only one collection.',
                level=messages.ERROR)
        else:
            # Send parse data command to celery
            collection = queryset[0]
            collection.parse.delay()

            self.message_user(request,
                "Parsing shapefile asynchronously, please check the collection parse log for status")

    def compute_value_count(self, request, queryset):

        form = None
        layer = queryset[0]

        # After posting, set the new name to file field
        if 'apply' in request.POST:
            form = SelectLayerActionForm(request.POST)
            if form.is_valid():
                rasterlayers = form.cleaned_data['rasterlayers']
                simplified = form.cleaned_data['simplified']
                for rst in rasterlayers:
                    compute_value_count.delay(layer, rst.id, simplified=simplified, compute_area=True)
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
                'simplified': True
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

admin.site.register(AggregationArea)
admin.site.register(ValueCountResult, ValueCountResultAdmin)
admin.site.register(AggregationLayer, ComputeActivityAggregatesModelAdmin)
