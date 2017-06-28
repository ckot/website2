# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.contrib import admin

from exp2.admin import (ExpsBaseModelAdmin, ExpsBaseTabularInline,
                        ExpsCollapsableTabularInline,
                        add_inline_to_experiment, experiment_inline_positions)

from . import models

class ScenarioInline(ExpsCollapsableTabularInline):
    model = models.Scenario

add_inline_to_experiment(ScenarioInline,
                         experiment_inline_positions.BEFORE_TASKS)
