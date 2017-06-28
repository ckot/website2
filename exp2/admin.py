# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from collections import namedtuple
from pprint import PrettyPrinter

from django.core.urlresolvers import resolve
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import register
from django.contrib.contenttypes.models import ContentType
from django.contrib.staticfiles import finders
from django.db.models import TextField
from django.forms import Textarea, formset_factory
from django.forms.models import modelformset_factory
from django.utils.safestring import mark_safe


from hier_models.admin import NonTopLevelModelMixin

from . import forms
from . import models

PP = PrettyPrinter(indent=4)

_foo = namedtuple('ExperimentInlinePosition',
                  ['BEFORE_TASKS', 'TASKS', 'AFTER_TASKS'])
experiment_inline_positions = _foo('BEFORE_TASKS', 'TASKS', 'AFTER_TASKS')


def auto_set_app(db_field, app_label, **kwargs):
    if db_field.name == 'app':
        # print "db field is app"
        qs = models.App.objects.filter(app_label=app_label)
        app = qs.first()
        if app:
            # print "app.id: %s" % app.id
            kwargs['initial'] = app.id
            kwargs['queryset'] = qs
    return kwargs

def add_inline_to_experiment(inline_to_add, inline_position):
    inlines = admin.site._registry[models.Experiment].inlines
    pre_task_subclass_inlines = []
    task_subclass_inlines = []
    post_task_subclass_inlines = []
    found_task_inline = False
    for inline in inlines:
        if found_task_inline:
            if issubclass(inline.model, models.ExperimentalTask):
                task_subclass_inlines.append(inline)
            else:
                post_task_subclass_inlines.append(inline)
        else:
            if issubclass(inline.model, models.ExperimentalTask):
                found_task_inline = True
                task_subclass_inlines.append(inline)
            else:
                pre_task_subclass_inlines.append(inline)
    if experiment_inline_positions.BEFORE_TASKS == inline_position:
        pre_task_subclass_inlines.append(inline_to_add)
    elif experiment_inline_positions.TASKS == inline_position:
        task_subclass_inlines.append(inline_to_add)
    else:
        post_task_subclass_inlines.append(inline_to_add)
    tmp = pre_task_subclass_inlines + \
        task_subclass_inlines + \
        post_task_subclass_inlines
    admin.site._registry[models.Experiment].inlines = tmp

def get_parent_object_for_inline(self, request):
    """NOTE: this is a function, you must pass in 'self'"""
    resolved = resolve(request.path_info)
    obj = None
    if resolved.args:
        obj = self.parent_model.objects.get(pk=resolved.args[0])
    return obj

def inherit_parent_val_on_inline_creation(self,
                                         request, db_field, attribute, **kwargs):
    """NOTE: this a function, 'self' needs to be passed in"""
    if db_field.name == attribute:
        parent = get_parent_object_for_inline(self, request)
        if parent:
            if hasattr(parent, attribute):
                val = getattr(parent, attribute)
                kwargs['initial'] = val
    return kwargs

def inherit_initial_vals_from_parent(self,
                                     db_field, request, attributes, **kwargs):
    fld_name = db_field.name
    print "field name: %s" % fld_name
    print "attributes: %s" % attributes
    if fld_name in attributes:
        print "%s in %s" % (fld_name, attributes)
        parent = get_parent_object_for_inline(self, request)
        if parent:
            print "parent found: %s" % parent
            if hasattr(parent, fld_name):
                print "parent has attribute: %s" % fld_name
                val = getattr(parent, fld_name)
                print "setting initial val to: %s" % val
                kwargs['initial'] = val
    return kwargs

# base models
class ExpsBaseModelAdmin(admin.ModelAdmin):
    save_on_top = True
    formfield_overrides = {
        TextField: {'widget': Textarea(attrs={'cols': 120, 'rows': 4})}
    }


class ExpsBaseTabularInline(admin.TabularInline):
    show_change_link = True
    extra = 0


class ExpsCollapsableTabularInline(ExpsBaseTabularInline):
    classes = ['collapse']


# inlines
class GenericTaskInline(ExpsCollapsableTabularInline):
    model = models.GenericTask


class TaskParameterInline(ExpsBaseTabularInline):
    model = models.TaskParameter


class ConditionInline(ExpsBaseTabularInline):
    model = models.Condition


class OrderedTaskInline(ExpsBaseTabularInline):
    model = models.OrderedTask

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'task':
            cond = get_parent_object_for_inline(self, request)
            if cond:
                kwargs['queryset'] = models.ExperimentalTask\
                                           .objects\
                                           .filter(pk__in=cond.experiment.tasks.all())
        return super(OrderedTaskInline, self).formfield_for_choice_field(db_field,
                                                                         request,
                                                                         **kwargs)


class FacilityInline(ExpsBaseTabularInline):
    model = models.Facility


class SectionInline(ExpsBaseTabularInline):
    model = models.Section
    form = forms.SectionInlineForm
    formset = forms.GetParentFormSet


class ParticipantInline(ExpsBaseTabularInline):
    model = models.Participant
    fields = ('uid', 'condition', 'assigned_to_user')
    readonly_fields = ('uid', 'condition', 'assigned_to_user')
    template = 'admin/exp2/participant/edit_inline/tabular.html'

    def assigned_to_user(self, obj):
        filename = "admin/img/icon-%s.svg" % "no" if obj.user is None else "yes"
        url = settings.STATIC_URL + filename
        return mark_safe("""<img src="%s" />""" % url)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'condition':
            resolved = resolve(request.path_info)
            if resolved.args:
                pk = resolved.args[0]
                section = models.Section.objects.get(pk=pk)
                if section:
                    conds = section.facility.experiment.conditions.all()
                    kwargs['queryset'] = conds
        return super(ParticipantInline, self).formfield_for_foreignkey(db_field,
                                                                       request,
                                                                       **kwargs)


# modeladmins
@register(models.App)
class AppAdmin(ExpsBaseModelAdmin):
    fields = ('name', 'app_label', 'task_type')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'task_type':
            ct_ids = []
            for ct in ContentType.objects.all():
                ct_mdl = ct.model_class()
                if issubclass(ct_mdl, models.ExperimentalTask) and \
                   ct_mdl != models.ExperimentalTask:
                    ct_ids.append(ct.id)
            kwargs['queryset'] = ContentType.objects.filter(pk__in=ct_ids)
        return super(AppAdmin, self).formfield_for_foreignkey(db_field,
                                                              request,
                                                              **kwargs)


@register(models.Experiment)
class ExperimentAdmin(ExpsBaseModelAdmin):
    fields = ('name', 'desc')
    inlines = [GenericTaskInline, ConditionInline, FacilityInline]


@register(models.GenericTask)
class GenericTaskAdmin(ExpsBaseModelAdmin):
    fields = ('experiment', 'name', 'app', 'task_type')
    readonly_fields = ('experiment',)
    inlines = [TaskParameterInline]


@register(models.Condition)
class ConditionAdmin(NonTopLevelModelMixin, ExpsBaseModelAdmin):
    fields = ('experiment', 'name', 'enforce_training_task_order')
    readonly_fields = ('experiment',)
    inlines = [OrderedTaskInline]


@register(models.Facility)
class FacilityAdmin(NonTopLevelModelMixin, ExpsBaseModelAdmin):
    fields = (('experiment', 'name'),
              ('pre_training_tasks_enabled', 'toggle_pre_training_tasks_enabled_at'),
              ('training_tasks_enabled', 'toggle_training_tasks_enabled_at'),
              ('post_training_tasks_enabled', 'toggle_post_training_tasks_enabled_at'))
    readonly_fields = ('experiment',)
    inlines = [SectionInline]

    def save_formset(self, request, form, formset, change):
        # in the section inlines, we set inherit the bool field
        # values from the Facility as 'initial' values.  since these
        # 'initial' values may be changed in the inline form, we need
        # to pass skip_inheritance=True kwarg to Section.save() so that
        # it doesn't clobber whatever value might have been changed in the inline
        kwargs = {}
        if formset.model == models.Section:
            kwargs = {'skip_inheritance': True}
        instances = formset.save(commit=False)
        for instance in instances:
            instance.save(**kwargs)


def create_bulk_add_change_form(request, exp_id):
    """returns bound form (if returning with errors) else unbound form"""
    form = None
    # initial data is None unless the view has redirected here with errors
    # and filled in values for the fields (using session object)
    initial_data = request.session.pop("bulk_add_change_initial_data", None)
    if initial_data is not None:
        # have initial data - create a bound form
        form = forms.BulkParticipantConditionsForm(initial_data, exp_id=exp_id)
    else:
        # no initial data - create unbound form
        form = forms.BulkParticipantConditionsForm(exp_id=exp_id)
    return form


def create_bulk_delete_form(request):
    """returns bound form (if returning with errors) else unbound form"""
    form = None
    # initial data None unless the view has redirected here with errors
    # and filled in values for the fields (using session object)
    initial_data = request.session.pop('bulk_delete_initial_data', None)
    if initial_data is not None:
        form = forms.BulkSectionParticipantsForm(initial_data)
    else:
        form = forms.BulkSectionParticipantsForm()
    return form

@register(models.Section)
class SectionAdmin(NonTopLevelModelMixin, ExpsBaseModelAdmin):
    fields = ('facility', 'name',
              ('pre_training_tasks_enabled', 'toggle_pre_training_tasks_enabled_at'),
              ('training_tasks_enabled', 'toggle_training_tasks_enabled_at'),
              ('post_training_tasks_enabled', 'toggle_post_training_tasks_enabled_at'))
    readonly_fields = ('facility',)
    inlines = [ParticipantInline]

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """adds forms for Bulk Add/Change and Bulk Delete to context"""
        section = models.Section.objects.filter(pk=object_id)\
                                        .prefetch_related("facility__experiment",
                                                          "participants")\
                                        .first()
        exp_id = section.facility.experiment.id
       # create bulk forms
        bulk_add_change_frm = create_bulk_add_change_form(request, exp_id)
        bulk_del_frm = create_bulk_delete_form(request)
        # attach site id and bulk forms to 'extra_context'
        extra_context = extra_context or {}
        extra_context['section_id'] = object_id
        extra_context["bulk_add_change_form"] = bulk_add_change_frm
        extra_context['bulk_delete_form'] = bulk_del_frm
        # print extra_context
        return super(SectionAdmin, self).change_view(
            request, object_id, form_url, extra_context=extra_context)


@register(models.Participant)
class ParticipantAdmin(NonTopLevelModelMixin, ExpsBaseModelAdmin):
    fields = ('user',
              ('uid', 'section', 'condition'),
              'enforce_training_task_order',
              ('pre_training_tasks_enabled',
               'training_tasks_enabled',
               'post_training_tasks_enabled'),
              'decommissioned')
    readonly_fields = ('user', 'section', 'uid')
