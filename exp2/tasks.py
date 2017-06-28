# Create your tasks here
from __future__ import absolute_import, unicode_literals

from django.contrib.contenttypes.models import ContentType

import redis
import celery
from celery import shared_task
# from . import models

@shared_task
def add(x, y):
    return x + y

def args_to_key(args):
    return ":".join([str(arg) for arg in args])


def obj_field_name_to_key(obj, field_name):
    al = obj._meta.app_label
    mdl = obj.meta.object_name.lower()
    return "%s:%s:%s:%s" % (al, mdl, obj.pk, field_name)

class RevokableTask(celery.Task):

    def delete_key_from_scheduled_tasks(self, args, task_id):
        """
        scheduledtasks is a redis hash whos keys point to task_ids
        It's purpose is to allow key lookup (generated from task's args) and
        get the associated task_id, so that it can be revoked.

        this method shall be called whenever a task has completed so as to
        purge old keys
        """
        key = args_to_key(args)
        conn = redis.StrictRedis()
        # value, if exists is the task id associated with key
        value = conn.hget("scheduledtasks", key)
        if value and value == task_id:
            print "have match, deleting %s from scheduledtasks" % key
            conn.hdel("scheduledtasks", key)

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        super(RevokableTask, self).after_return(status, retval, task_id, args, kwargs, einfo)
        self.delete_key_from_scheduled_tasks(args, task_id)

    # def on_failure(self, exc, task_id, args, kwargs, einfo):
    #     super(RevokableTask, self).on_failure(exc, task_id, args, kwargs, einfo)
    #     self.delete_key_from_scheduled_tasks(args)
    #
    # def on_success(self, retval, task_id, args, kwargs):
    #     super(RevokableTask, retval, task_id, args, kwargs)
    #     self.delete_key_from_scheduled_tasks(args)
    #

def toggle_obj_bool_fld(obj, fld_to_toggle):
    success = False
    try:
        # get the current value
        orig_val = getattr(obj, fld_to_toggle)
        # since this is boolean,new_val is simply not orig_val
        new_val = not orig_val
        setattr(obj, fld_to_toggle, new_val)
        # the name of the field which scheduled this toggling is
        # 'toggle_<fld_to_toggle>_at', now that we've done the toggling
        # set the value to None
        sched_attr = "toggle_%s_at" % fld_to_toggle
        setattr(obj, sched_attr, None)
        obj.save()
        success = True
    except Exception:
        pass
    return success

@shared_task(base=RevokableTask)
def toggle_object_fldname_value(app_label, model, pk, fld_name):
    ct = ContentType.objects.get(app_label=app_label, model=model)
    mdl = ct.model_class()
    obj = mdl.objects.get(pk=pk)
    return toggle_obj_bool_fld(obj, fld_name)

#
# @shared_task
# def toggle_facility_bool_field_at(facility_id, fld_to_toggle):
#     fac = models.Facility.objects.get(pk=facility_id)
#     return toggle_obj_bool_fld(fac, fld_to_toggle)
#
# @shared_task
# def toggle_section_bool_field_at(section_id, fld_to_toggle):
#     sec = models.Section.objects.get(pk=section_id)
#     return toggle_obj_bool_fld(sec, fld_to_toggle)
