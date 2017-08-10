# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-10 20:34
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0035_auto_20170810_1245'),
    ]

    operations = [
        migrations.AddField(
            model_name='sampledredditthread',
            name='day_of_month',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='day_of_week',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='hour',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='title_length',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='day_of_month',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='day_of_week',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='hour',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
