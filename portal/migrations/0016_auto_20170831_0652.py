# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-31 06:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0015_auto_20170830_2033'),
    ]

    operations = [
        migrations.AddField(
            model_name='sampledredditthread',
            name='has_other_link',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='has_other_link',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]