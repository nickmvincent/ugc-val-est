# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-13 16:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0044_auto_20170813_1051'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stackoverflowanswer',
            name='owner_user_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
