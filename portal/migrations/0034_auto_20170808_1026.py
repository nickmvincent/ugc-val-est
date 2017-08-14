# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-08 15:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0033_auto_20170805_2143'),
    ]

    operations = [
        migrations.CreateModel(
            name='StackOverflowAnswer',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=192)),
                ('body', models.CharField(max_length=58431)),
                ('accepted_answer_id', models.IntegerField()),
                ('answer_count', models.IntegerField()),
                ('comment_count', models.IntegerField()),
                ('community_owned_date', models.DateTimeField()),
                ('creation_date', models.DateTimeField()),
                ('favorite_count', models.IntegerField()),
                ('last_activity_date', models.DateTimeField()),
                ('last_edit_date', models.DateTimeField()),
                ('last_editor_display_name', models.CharField(max_length=30)),
                ('last_editor_user_id', models.IntegerField()),
                ('owner_display_name', models.CharField(max_length=30)),
                ('owner_user_id', models.IntegerField()),
                ('post_type_id', models.IntegerField()),
                ('score', models.IntegerField()),
                ('tags', models.CharField(max_length=115)),
                ('view_count', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='StackOverflowQuestion',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=192)),
                ('body', models.CharField(max_length=58431)),
                ('accepted_answer_id', models.IntegerField()),
                ('answer_count', models.IntegerField()),
                ('comment_count', models.IntegerField()),
                ('community_owned_date', models.DateTimeField()),
                ('creation_date', models.DateTimeField()),
                ('favorite_count', models.IntegerField()),
                ('last_activity_date', models.DateTimeField()),
                ('last_edit_date', models.DateTimeField()),
                ('last_editor_display_name', models.CharField(max_length=30)),
                ('last_editor_user_id', models.IntegerField()),
                ('owner_display_name', models.CharField(max_length=30)),
                ('owner_user_id', models.IntegerField()),
                ('post_type_id', models.IntegerField()),
                ('score', models.IntegerField()),
                ('tags', models.CharField(max_length=115)),
                ('view_count', models.IntegerField()),
            ],
        ),
        migrations.RemoveField(
            model_name='sampledstackoverflowpost',
            name='tags',
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='day_of_avg_score',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='day_prior_avg_score',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sampledredditthread',
            name='week_after_avg_score',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='day_of_avg_score',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='day_prior_avg_score',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sampledstackoverflowpost',
            name='week_after_avg_score',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='sampledredditthread',
            name='context',
            field=models.CharField(blank=True, max_length=115, null=True),
        ),
        migrations.AlterField(
            model_name='sampledstackoverflowpost',
            name='context',
            field=models.CharField(blank=True, max_length=115, null=True),
        ),
        migrations.AlterField(
            model_name='sampledstackoverflowpost',
            name='tags_string',
            field=models.CharField(blank=True, max_length=115, null=True),
        ),
        migrations.DeleteModel(
            name='Tag',
        ),
    ]