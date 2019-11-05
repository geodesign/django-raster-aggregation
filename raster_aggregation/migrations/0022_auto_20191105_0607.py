# Generated by Django 2.1.7 on 2019-11-05 06:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster_aggregation', '0021_auto_20190905_0754'),
    ]

    operations = [
        migrations.AddField(
            model_name='valuecountresult',
            name='range_max',
            field=models.FloatField(blank=True, help_text='Upper cutoff limit for valuecounts. Only used if lower cutoff is also specified.', null=True),
        ),
        migrations.AddField(
            model_name='valuecountresult',
            name='range_min',
            field=models.FloatField(blank=True, help_text='Lower cutoff limit for valuecounts. Only used if upper cutoff is also specified.', null=True),
        ),
    ]
