# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-13 05:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0041_auto_20170812_2338'),
    ]

    operations = [
        migrations.AlterField(
            model_name='redditpost',
            name='subreddit_id',
            field=models.CharField(blank=True, max_length=8, null=True),
        ),
    ]