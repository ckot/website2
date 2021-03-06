# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-28 18:05
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exp2', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='facility',
            name='toggle_post_training_tasks_enabled_at',
            field=models.DateTimeField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='facility',
            name='toggle_pre_training_tasks_enabled_at',
            field=models.DateTimeField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='facility',
            name='toggle_training_tasks_enabled_at',
            field=models.DateTimeField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='section',
            name='toggle_post_training_tasks_enabled_at',
            field=models.DateTimeField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='section',
            name='toggle_pre_training_tasks_enabled_at',
            field=models.DateTimeField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='section',
            name='toggle_training_tasks_enabled_at',
            field=models.DateTimeField(default=None, null=True),
        ),
    ]
