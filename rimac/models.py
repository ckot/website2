# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from exp2.models import Asset, Experiment, ExperimentalTask
from dt.models import Scenario

@python_2_unicode_compatible
class Problem(Asset):
    name = models.CharField(max_length=64,
                            null=False,
                            blank=False,
                            unique=True)

    def __str__(self):
        return self.name


class RimacTask(ExperimentalTask):
    scenario = models.ForeignKey(Scenario,
                                 null=False,
                                 blank=False,
                                 on_delete=models.CASCADE,
                                 related_name='+')
    problem = models.ForeignKey('Problem',
                                null=False,
                                blank=False,
                                on_delete=models.CASCADE,
                                related_name='+')
