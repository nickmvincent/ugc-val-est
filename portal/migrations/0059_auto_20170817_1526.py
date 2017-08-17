# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-17 15:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0058_auto_20170817_0335'),
    ]

    operations = [
        migrations.AddField(
            model_name='sampledredditthread',
            name='num_major_edits',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='num_minor_edits',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='num_major_edits',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='num_minor_edits',
            field=models.IntegerField(default=0),
        ),
    ]
