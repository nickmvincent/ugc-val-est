# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-02 19:43
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0021_auto_20170802_1428'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='PostSpecificWikiLink',
            new_name='PostSpecificWikiScores',
        ),
    ]
