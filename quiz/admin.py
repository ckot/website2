# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from exp2.models import App

from exp2.admin import (ExpsBaseModelAdmin, ExpsBaseTabularInline,
                        ExpsCollapsableTabularInline,
                        add_inline_to_experiment, experiment_inline_positions,
                        get_parent_object_for_inline,
                        TaskParameterInline, auto_set_app)
from . import models

class QuizTaskInline(ExpsCollapsableTabularInline):
    model = models.QuizTask
    show_change_link = False
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        kwargs = auto_set_app(db_field, 'quiz', **kwargs)
        return super(QuizTaskInline, self).formfield_for_foreignkey(db_field,
                                                                    request,
                                                                    **kwargs)


@admin.register(models.Quiz)
class QuizAdmin(ExpsBaseModelAdmin):
    pass

# @admin.register(models.QuizTask)
# class QuizTaskAdmin(ExpsBaseModelAdmin):
#     fields = ('experiment', 'app', 'name', 'label', 'task_type', 'quiz')
#     readonly_fields = ('experiment', 'app')
#     # inlines = [TaskParameterInline]
#     # pass

add_inline_to_experiment(QuizTaskInline,
                         experiment_inline_positions.TASKS)
