# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-14 20:42
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0047_auto_20170814_1752'),
    ]

    operations = [
        migrations.AlterField(
            model_name='redditpost',
            name='author_flair_css_class',
            field=models.CharField(blank=True, max_length=95, null=True),
        ),
        migrations.AlterField(
            model_name='redditpost',
            name='author_flair_text',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AlterField(
            model_name='redditpost',
            name='domain',
            field=models.CharField(max_length=275),
        ),
        migrations.AlterField(
            model_name='redditpost',
            name='link_flair_css_class',
            field=models.CharField(blank=True, max_length=102, null=True),
        ),
        migrations.AlterField(
            model_name='redditpost',
            name='link_flair_text',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AlterField(
            model_name='redditpost',
            name='permalink',
            field=models.CharField(max_length=131),
        ),
        migrations.AlterField(
            model_name='redditpost',
            name='selftext',
            field=models.CharField(max_length=74185),
        ),
        migrations.AlterField(
            model_name='redditpost',
            name='subreddit',
            field=models.CharField(blank=True, max_length=24, null=True),
        ),
        migrations.AlterField(
            model_name='redditpost',
            name='title',
            field=models.CharField(max_length=1182),
        ),
        migrations.AlterField(
            model_name='redditpost',
            name='url',
            field=models.CharField(max_length=31215),
        ),
    ]
