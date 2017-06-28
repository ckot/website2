# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.core.urlresolvers import resolve


from exp2.admin import (ExpsBaseModelAdmin, ExpsBaseTabularInline,
                        ExpsCollapsableTabularInline,
                        add_inline_to_experiment, experiment_inline_positions,
                        get_parent_object_for_inline,
                        TaskParameterInline, auto_set_app)
from . import models

class RimacTaskInline(ExpsBaseTabularInline):
    model = models.RimacTask

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        kwargs = auto_set_app(db_field, 'rimac', **kwargs)
        if db_field.name == 'scenario':
            exp = get_parent_object_for_inline(self, request)
            if exp:
                kwargs['queryset'] = models.Scenario.objects\
                                                    .filter(experiment=exp)
        return super(RimacTaskInline, self).formfield_for_foreignkey(db_field,
                                                                     request,
                                                                     **kwargs)

@admin.register(models.Problem)
class ProblemAdmin(admin.ModelAdmin):
    pass

@admin.register(models.RimacTask)
class RimacTaskAdmin(admin.ModelAdmin):
    # fields = ('experiment', )
    # inlines = [TaskParameterInline]
    pass

add_inline_to_experiment(RimacTaskInline,
                         experiment_inline_positions.TASKS)
