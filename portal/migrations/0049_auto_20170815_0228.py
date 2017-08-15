# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-15 02:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0048_auto_20170814_2042'),
    ]

    operations = [
        migrations.AddField(
            model_name='sampledredditthread',
            name='body_flesch_kincaid_grade',
            field=models.DecimalField(decimal_places=1, default=0, max_digits=3),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='title_flesch_kincaid_grade',
            field=models.DecimalField(decimal_places=1, default=0, max_digits=3),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='body_flesch_kincaid_grade',
            field=models.DecimalField(decimal_places=1, default=0, max_digits=3),
        ),
    ]