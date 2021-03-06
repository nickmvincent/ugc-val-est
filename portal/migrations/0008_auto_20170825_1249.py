# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-25 12:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0007_auto_20170824_1341'),
    ]

    operations = [
        migrations.AddField(
            model_name='sampledredditthread',
            name='num_new_editors_prev_week',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='num_new_editors_retained_prev_week',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='num_new_edits_prev_week',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='num_old_edits_prev_week',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='num_new_editors_prev_week',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='num_new_editors_retained_prev_week',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='num_new_edits_prev_week',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='num_old_edits_prev_week',
            field=models.IntegerField(default=0),
        ),
    ]
