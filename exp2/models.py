# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from collections import namedtuple

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
# from django.db.models import Q
from django.utils.encoding import python_2_unicode_compatible

from dirtyfields import DirtyFieldsMixin

from .tasks import args_to_key, obj_field_name_to_key, toggle_obj_bool_fld

_tt = namedtuple('TaskType', ['PRE_TRAINING', 'TRAINING', 'POST_TRAINING'])
TASK_TYPES = _tt('PRE_TRAINING_TASK', 'TRAINING_TASK', 'POST_TRAINING_TASK')

class FieldPropagatorMixin(object):

    def get_field_vals_to_propagate(self, dirty_fields):
        new_vals = {}
        print "%s: checking for propagated_fields: %s" % \
            (self, self.propagated_fields)
        if len(self.propagated_fields) and len(dirty_fields):
            for fld in dirty_fields:
                if fld in self.propagated_fields:
                    new_vals[fld] = getattr(self, fld)
        return new_vals

    def propagate_fld_vals_to_children(self, children_qs, new_vals):
        for child in children_qs.all():
            child_altered = False
            for fld in new_vals:
                parent_val = new_vals[fld]
                ch_old_val = getattr(child, fld)
                if parent_val != ch_old_val:
                    child_altered = True
                    setattr(child, fld, parent_val)
                    print ("%s:%s value propagated from parent:%s. Value "
                           "changed from from %s to %s") % \
                           (child, fld, self, ch_old_val, parent_val)
            if child_altered:
                child.save()

    @property
    def propagated_fields(self):
        return NotImplemented


class FieldInheritorMixin(object):

    def get_inherited_vals_from_parent(self, parent):
        parent_vals = {}
        if parent:
            for fld in self.inherited_fields:
                if hasattr(parent, fld):
                    parent_vals[fld] = getattr(parent, fld)
        return parent_vals

    def inherit_vals_from_parent(self, parent):
        if parent:
            parent_vals = self.get_inherited_vals_from_parent(parent)
            for fld in parent_vals:
                parent_val = parent_vals[fld]
                orig_val = getattr(self, fld)
                setattr(self, fld, parent_val)
                new_val = getattr(self, fld)
                print "%s:%s value(%s) inherited from %s. Original value(%s)" % \
                    (self, fld, new_val, parent, orig_val)

    @property
    def inherited_fields(self):
        return NotImplemented

class ScheduleableFieldMixin(object):

    def get_schedulable_fld_changes(self, dirty_fields):
        flds_to_schedule = []
        sched_flds_to_cancel = []
        print "%s checking for scheduled field changes: %s" % \
            (self, self.schedulable_fields)
        print "%s dirty fields: %s" % (self, dirty_fields)
        for field in self.schedulable_fields:
            if field in dirty_fields:
                orig_val = dirty_fields[field]
                new_val = getattr(self, field)
                print ("get_schedulable_fld_changes:  "
                       "%s - orig_val: %s  new_val: %s") % (field, orig_val, new_val)

                if orig_val is None and new_val is not None:
                    flds_to_schedule.append(field)
                elif orig_val is not None and new_val is None:
                    sched_flds_to_cancel.append(field)
                else:
                    print "get_schedulable_fld_changes: not sure what to do"
        return (flds_to_schedule, sched_flds_to_cancel)


    def schedule_field_change(self, fld_name):
        key = "schedule_field_change:  %s:%s:%s:%s" % \
            (self._meta.app_label, self._meta.object_name.lower(), self.pk, fld_name)
        print key

    def cancel_field_change(self, fld_name):
        key = "cancel_field_change:  %s:%s:%s:%s" % \
            (self._meta.app_label, self._meta.object_name.lower(), self.pk, fld_name)
        print key

    @property
    def schedulable_fields(self):
        return NotImplemented


class Asset(models.Model):
    pass


@python_2_unicode_compatible
class App(models.Model):
    name = models.CharField(max_length=64,
                            unique=True,
                            null=False,
                            blank=False)
    app_label = models.CharField(max_length=32,
                                 null=True,
                                 blank=True,
                                 default="",
                                 help_text=("only necessary if this has a "
                                            "dedicated django app. not needed "
                                            "for apps which use generic tasks"))
    task_type = models.ForeignKey(ContentType,
                                  null=False,
                                  blank=False,
                                  on_delete=models.CASCADE,
                                  help_text=("the value of this field is used "
                                             "to bind a data object (this) to "
                                             "the proper class in the code"))
    def __str__(self):
        return self.name



@python_2_unicode_compatible
class Experiment(models.Model):
    name = models.CharField(max_length=64,
                            unique=True,
                            null=False,
                            blank=False)
    desc = models.TextField(default="",
                            blank=True)
    def __str__(self):
        return self.name


@python_2_unicode_compatible
class ExperimentalTask(models.Model):
    TASK_TYPE_CHOICES = [
        (TASK_TYPES.PRE_TRAINING, "Pre-Training Task"),
        (TASK_TYPES.TRAINING, "Training Task"),
        (TASK_TYPES.POST_TRAINING, "Post-Training Task")
    ]

    experiment = models.ForeignKey('Experiment',
                                   null=False,
                                   blank=False,
                                   on_delete=models.CASCADE,
                                   related_name='tasks')
    app = models.ForeignKey('App',
                            null=False,
                            blank=False,
                            on_delete=models.CASCADE,
                            related_name='+')
    name = models.CharField(max_length=64,
                            null=False,
                            blank=False,
                            help_text=("descriptive for Experimenter "
                                       "must be unique within Experiment"))
    label = models.CharField(max_length=64,
                             null=False,
                             blank=False,
                             help_text=("what user sees in their task list "
                                        "does not need to be unique"))
    task_type = models.CharField(max_length=32,
                                 choices=TASK_TYPE_CHOICES,
                                 null=False,
                                 blank=False,
                                 default=TASK_TYPES.TRAINING)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('experiment', 'name')


class TaskParameter(models.Model):
    task = models.ForeignKey('ExperimentalTask',
                             null=False,
                             blank=False,
                             on_delete=models.CASCADE,
                             related_name='task_parameters')
    name = models.CharField(max_length=64,
                            null=False,
                            blank=False)
    value = models.CharField(max_length=1024,
                             null=False,
                             blank=False)

    class Meta:
        unique_together = ('task', 'name')

class GenericTask(ExperimentalTask):
    pass

@python_2_unicode_compatible
class Condition(FieldPropagatorMixin, DirtyFieldsMixin, models.Model):
    experiment = models.ForeignKey('Experiment',
                                   null=False,
                                   blank=False,
                                   on_delete=models.CASCADE,
                                   related_name='conditions')
    name = models.CharField(max_length=64,
                            null=False,
                            blank=False)
    enforce_training_task_order = models.BooleanField(default=True)
    propagated_fields = ['enforce_training_task_order']

    def __str__(self):
        return self.name

    @property
    def parent(self):
        return self.experiment

    def save(self, *args, **kwargs):
        new_vals = self.get_field_vals_to_propagate(self.get_dirty_fields())
        super(Condition, self).save(*args, **kwargs)
        if new_vals:
            self.propagate_fld_vals_to_children(self.participants, new_vals)

    class Meta:
        unique_together = ('experiment', 'name')



class OrderedTask(models.Model):
    condition = models.ForeignKey('Condition',
                                  null=False,
                                  blank=False,
                                  on_delete=models.CASCADE,
                                  related_name='ordered_tasks')
    order = models.PositiveIntegerField(null=False,
                                        blank=False)
    task = models.ForeignKey('ExperimentalTask',
                             null=False,
                             blank=False,
                             on_delete=models.CASCADE,
                             related_name='+')

    class Meta:
        ordering = ('order',)


@python_2_unicode_compatible
class Facility(ScheduleableFieldMixin, FieldPropagatorMixin, DirtyFieldsMixin,
               models.Model):
    experiment = models.ForeignKey('Experiment',
                                   null=False,
                                   blank=False,
                                   on_delete=models.CASCADE,
                                   related_name='facilities')
    name = models.CharField(max_length=64,
                            null=False,
                            blank=False)
    pre_training_tasks_enabled = models.BooleanField(default=True)
    training_tasks_enabled = models.BooleanField(default=True)
    post_training_tasks_enabled = models.BooleanField(default=True)
    toggle_pre_training_tasks_enabled_at = models.DateTimeField(null=True,
                                                                blank=True,
                                                                default=None)
    toggle_training_tasks_enabled_at = models.DateTimeField(null=True,
                                                            blank=True,
                                                            default=None)
    toggle_post_training_tasks_enabled_at = models.DateTimeField(null=True,
                                                                 blank=True,
                                                                 default=None)
    propagated_fields = ['pre_training_tasks_enabled',
                         'training_tasks_enabled',
                         'post_training_tasks_enabled']
    schedulable_fields = ['toggle_pre_training_tasks_enabled_at',
                          'toggle_training_tasks_enabled_at',
                          'toggle_post_training_tasks_enabled_at']

    def __str__(self):
        return self.name

    @property
    def parent(self):
        return self.experiment

    def save(self, *args, **kwargs):
        df = self.get_dirty_fields()
        new_vals = self.get_field_vals_to_propagate(df)
        flds_to_sched, sched_flds_to_cancel = self.get_schedulable_fld_changes(df)
        super(Facility, self).save(*args, **kwargs)
        if new_vals:
            self.propagate_fld_vals_to_children(self.sections, new_vals)
        if flds_to_sched:
            for fld in flds_to_sched:
                self.schedule_field_change(fld)
        if sched_flds_to_cancel:
            for fld in sched_flds_to_cancel:
                self.cancel_field_change(fld)

    class Meta:
        unique_together = ('experiment', 'name')
        verbose_name_plural = 'Facilities'


@python_2_unicode_compatible
class Section(ScheduleableFieldMixin, FieldInheritorMixin,
              FieldPropagatorMixin, DirtyFieldsMixin,
              models.Model):
    facility = models.ForeignKey('Facility',
                                 null=False,
                                 blank=False,
                                 on_delete=models.CASCADE,
                                 related_name='sections')
    name = models.CharField(max_length=64,
                            null=False,
                            blank=False)
    pre_training_tasks_enabled = models.BooleanField(default=True)
    training_tasks_enabled = models.BooleanField(default=True)
    post_training_tasks_enabled = models.BooleanField(default=True)
    toggle_pre_training_tasks_enabled_at = models.DateTimeField(null=True,
                                                                blank=True,
                                                                default=None)
    toggle_training_tasks_enabled_at = models.DateTimeField(null=True,
                                                            blank=True,
                                                            default=None)
    toggle_post_training_tasks_enabled_at = models.DateTimeField(null=True,
                                                                 blank=True,
                                                                 default=None)

    inherited_fields = ['pre_training_tasks_enabled',
                        'training_tasks_enabled',
                        'post_training_tasks_enabled']
    propagated_fields = ['pre_training_tasks_enabled',
                         'training_tasks_enabled',
                         'post_training_tasks_enabled']
    schedulable_fields = ['toggle_pre_training_tasks_enabled_at',
                          'toggle_training_tasks_enabled_at',
                          'toggle_post_training_tasks_enabled_at']

    def __str__(self):
        return self.name

    @property
    def parent(self):
        return self.facility

    def save(self, *args, **kwargs):
        new_vals = {}
        flds_to_sched, sched_flds_to_cancel = [], []
        skip_inheritance = kwargs.pop('skip_inheritance', False)
        if self.pk is None:
            if skip_inheritance:
                print "save() called from admin, skipping value inheritance"
            else:
                self.inherit_vals_from_parent(self.facility)
        else:
            df = self.get_dirty_fields()
            new_vals = self.get_field_vals_to_propagate(df)
            flds_to_sched, sched_flds_to_cancel = self.get_schedulable_fld_changes(df)

        super(Section, self).save(*args, **kwargs)
        if new_vals:
            self.propagate_fld_vals_to_children(self.participants, new_vals)
        if flds_to_sched:
            for fld in flds_to_sched:
                self.schedule_field_change(fld)
        if sched_flds_to_cancel:
            for fld in sched_flds_to_cancel:
                self.cancel_field_change(fld)

    class Meta:
        unique_together = ('facility', 'name')

@python_2_unicode_compatible
class Participant(FieldInheritorMixin, DirtyFieldsMixin, models.Model):
    user = models.ForeignKey(User,
                             null=True,
                             blank=True,
                             on_delete=models.CASCADE,
                             related_name='participants')
    section = models.ForeignKey('Section',
                                null=False,
                                blank=False,
                                on_delete=models.CASCADE,
                                related_name='participants')
    condition = models.ForeignKey('Condition',
                                  null=True,
                                  blank=True,
                                  on_delete=models.SET_NULL,
                                  related_name='participants')
    uid = models.PositiveIntegerField()
    decommissioned = models.BooleanField(default=False)
    enforce_training_task_order = models.BooleanField(default=True)
    pre_training_tasks_enabled = models.BooleanField(default=True)
    training_tasks_enabled = models.BooleanField(default=True)
    post_training_tasks_enabled = models.BooleanField(default=True)
    inherited_fields = ['enforce_training_task_order',
                        'pre_training_tasks_enabled',
                        'training_tasks_enabled',
                        'post_training_tasks_enabled']


    def __str__(self):
        return "%s" % self.uid

    @property
    def parent(self):
        return self.section

    def save(self, *args, **kwargs):
        if self.pk is None:
            print "creating new participant"
            self.inherit_vals_from_parent(self.section)
            if self.condition is not None:
                self.inherit_vals_from_parent(self.condition)
        else:
            dfs = self.get_dirty_fields(check_relationship=True)
            if "condition" in dfs:
                print "participant's condition was changed"
                if self.condition is not None:
                    self.inherit_vals_from_parent(self.condition)
        super(Participant, self).save(*args, **kwargs)


    class Meta:
        unique_together = ('section', 'uid')
