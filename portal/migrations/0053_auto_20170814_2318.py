# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-15 04:18
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0052_auto_20170814_2213'),
    ]

    operations = [
        migrations.AddField(
            model_name='sampledredditthread',
            name='body_coleman_liau_index',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='body_percent_punctuation',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='body_percent_spaces',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='body_percent_uppercase',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='body_starts_capitalized',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='title_coleman_liau_index',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='title_percent_punctuation',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='title_percent_spaces',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='title_percent_uppercase',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='title_starts_capitalized',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='body_coleman_liau_index',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='body_percent_punctuation',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='body_percent_spaces',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='body_percent_uppercase',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='body_starts_capitalized',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='num_tags',
            field=models.IntegerField(default=0),
        ),
    ]