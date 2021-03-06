# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-22 20:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0002_auto_20170822_1429'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sampledredditthread',
            name='day_prior_avg_score',
        ),
        migrations.RemoveField(
            model_name='sampledstackoverflowpost',
            name='day_prior_avg_score',
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='num_pageviews',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='num_pageviews_prev_week',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='num_pageviews_prev_week',
            field=models.IntegerField(default=0),
        ),
    ]
