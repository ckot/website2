# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from exp2.models import Asset, Experiment

def scenario_upload_path(instance, filename):
    return "scenarios/%s/%s" % (instance.experiment.name, filename)

@python_2_unicode_compatible
class Scenario(Asset):
    experiment = models.ForeignKey(Experiment,
                                   null=False,
                                   blank=False,
                                   on_delete=models.CASCADE,
                                   related_name='scenarios')
    name = models.CharField(max_length=64,
                            null=False,
                            blank=False,
                            unique=True)
    scenario_file = models.FileField(upload_to=scenario_upload_path)

    def __str__(self):
        return self.name
