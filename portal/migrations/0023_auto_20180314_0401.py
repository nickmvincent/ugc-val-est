# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2018-03-14 04:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0022_wikilink_alt_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='sampledredditthread',
            name='num_wiki_increased_pageviews_day_of',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='num_wiki_increased_pageviews_day_of',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
