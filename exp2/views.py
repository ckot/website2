# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from collections import defaultdict
import itertools
# import logging
import os

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils import six, timezone
from django.views.decorators.http import require_POST

from . import models
from . import forms

# from django_tutalk.core.utils import (
#     pk_to_int_or_404, is_superuser, is_staff_or_superuser,
#     create_breadcrumbs, mk_context)
#
#
# LOGGER = logging.getLogger(__name__)


# def get_section_participants(section):
#     return models.Participant.objects\
#                              .prefetch_related("condition")\
#                              .filter(section__id=section.id)\
#                              .order_by("uid")\
#                              .all()


# def get_experiment_conditions(exp):
#     return models.Condition.objects\
#                            .filter(experiment_id=exp.id)\
#                            .order_by("name")\
#                            .all()
#
# def get_bulk_form_attributes(section, participants, conditions=None):
#     cond_names_re = r"^.+$"
#     if conditions is not None:
#         cond_names = [cond.name for cond in conditions]
#         joined_cond_names = "|".join(cond_names)
#         cond_names_re = r"^(?:%s)(?:,(?:%s))*$" % (joined_cond_names,
#                                                    joined_cond_names)
#     create_first_uid_min_value = None
#     create_first_uid_max_value = None
#     create_last_uid_min_value = None
#     create_last_uid_max_value = None
#     update_delete_first_uid_min_value = None
#     update_delete_first_uid_max_value = None
#     update_delete_last_uid_min_value = None
#     update_delete_last_uid_max_value = None
#
#     first_part = participants.first()
#     first_part_uid = None
#     last_part_uid = None
#     num_parts = len(participants)
#     if first_part is None:
#         create_first_uid_min_value = 1
#         create_last_uid_min_value = 1
#     else:
#         last_part = participants.last()
#         first_part_uid = first_part.uid
#         last_part_uid = last_part.uid
#         if (last_part_uid - first_part_uid) > num_parts:
#             # create_first_uid_min_value = first missing uid in range
#             part_uids = set([part.uid for part in participants])
#             all_uids = set(range(first_part_uid, last_part_uid + 1))
#             first_missing_uid = min(all_uids - part_uids)
#             create_first_uid_min_value = first_missing_uid
#             create_last_uid_min_value = first_missing_uid
#             del first_missing_uid
#         else:
#             create_first_uid_min_value = last_part_uid + 1
#             create_last_uid_min_value = last_part_uid + 1
#             update_delete_first_uid_min_value = first_part_uid
#             update_delete_first_uid_max_value = last_part_uid
#             update_delete_last_uid_min_value = first_part_uid
#             update_delete_last_uid_max_value = last_part_uid
#         del last_part
#     del first_part
#     ret_val = locals()
#     del ret_val["section"]
#     del ret_val["participants"]
#     if conditions is not None:
#         del ret_val["conditions"]
#         del ret_val["cond"]
#     # in case we have other vars we want returned, but aren't json serialable
#     log_data = copy.copy(ret_val)
#     # LOGGER.debug(json.dumps(log_data, indent=4))
#     return ret_val
#
#
# def initialize_bulk_forms(request, section, participants, bulk_form_attrs):
#     bulk_update_form = None
#     bulk_delete_form = None
#     bulk_create_url = section.get_bulk_participant_create_url()
#     bulk_update_url = ""
#     bulk_delete_url = ""
#

def get_pre_existing_participants(section_id, first_uid, last_uid):
    return models.Participant.objects.filter(section=section_id,
                                             uid__range=(first_uid, last_uid))\
                                     .order_by('uid')\
                                     .all()


def gen_uids_exist_error_message(pre_existing_parts):
    pre_existing_uids = ', '.join([six.text_type(p.uid)
                                   for p in pre_existing_parts])
    return "uids %s already exist" % pre_existing_uids


def gen_missing_uids_error_message(first_uid, last_uid, pre_existing_parts):
    """returns string listing the missing uids"""
    peps_dct = {pep.id: pep for pep in pre_existing_parts}
    missing_uids_str = ','.join([six.text_type(uid)
                                 for uid in range(first_uid, last_uid + 1)
                                 if uid not in peps_dct])
    return "uids '%s' don't exist" % missing_uids_str


def get_condition_cycler(cond_id_order, conditions):
    conds_dct = {cond.id: cond for cond in conditions}
    sorted_conds = [conds_dct[cond_id] for cond_id in cond_id_order]
    return itertools.cycle(sorted_conds)


def add_success_message(request, first_uid, last_uid, verb):
    messages.success(request,
                     "participants %d - %d successfully %s" %
                     (first_uid, last_uid, verb))


def add_warning(request, form_name):
    messages.warning(request,
                     "%s contains errors. See below" % form_name)


def add_error_message(request, form_name, error_message):
    messages.error(request,
                   "%s %s" % (form_name, error_message))


@require_POST
def section_bulk_participants_add_change(request, section_id=None):
    section = get_object_or_404(models.Section, pk=section_id)
    dest_url = reverse("admin:exp2_section_change", args=(section_id,))
    form = forms.BulkParticipantConditionsForm(request.POST,
                                               exp_id=section.facility.experiment.id)
    action = None
    if form.is_valid():
        first_uid = form.cleaned_data["first_uid"]
        last_uid = form.cleaned_data["last_uid"]
        action = form.cleaned_data["action"]
        # cleaned_data.conditions seems to sorted
        conditions = form.cleaned_data["conditions"]
        cond_id_order = [int(x) for x in request.POST.getlist("conditions")]
        pre_existing_parts = get_pre_existing_participants(
            section_id, first_uid, last_uid)
        if "create" == action and pre_existing_parts:
            err_msg = gen_uids_exist_error_message(pre_existing_parts)
            add_error_message(request, "Bulk Create/Update Form", err_msg)
        elif "update" == action and \
             len(pre_existing_parts) != (last_uid - first_uid) + 1:
            err_msg = gen_missing_uids_error_message(
                first_uid, last_uid, pre_existing_parts)
            add_error_message(request, "Bulk Create/Update Form", err_msg)
        else:
            cond_cycler = get_condition_cycler(cond_id_order, conditions)
            if "create" == action:
                parts = [models.Participant(uid=uid,
                                            section=section,
                                            condition=cond_cycler.next())
                         for uid in range(first_uid, last_uid + 1)]
                # pylint: disable=I0011,E1101
                # don't do a bulk_create, as Participant model's custom
                # won't be called (which inherits values from section and
                # condition )
                # models.Participant.objects.bulk_create(parts)
                for part in parts:
                    part.save()
                add_success_message(request, first_uid, last_uid, "added")
            elif "update" == action:
                for pe in pre_existing_parts:
                    pe.condition = cond_cycler.next()
                    pe.save()
                add_success_message(request, first_uid, last_uid, "updated")
            return HttpResponseRedirect(dest_url)
    else:
        add_warning(request, "Bulk Create/Update Participants")
    create_update_frm_set_init_vals(request)
    return HttpResponseRedirect(dest_url)


def create_update_frm_set_init_vals(request):
    initial_data = {
        "first_uid": six.text_type(request.POST.get("first_uid", "")),
        "last_uid": six.text_type(request.POST.get("last_uid", "")),
        "action": six.text_type(request.POST.get("action", "")),
        "conditions": [six.text_type(c)
                       for c in request.POST.getlist("conditions", [])]
    }
    request.session['bulk_create_update_initial_data'] = initial_data


def delete_frm_set_init_vals(request):
    initial_data = {
        "first_uid": six.text_type(request.POST.get("first_uid", "")),
        "last_uid": six.text_type(request.POST.get("last_uid", ""))
    }
    request.session['bulk_delete_initial_data'] = initial_data


@require_POST
def section_bulk_participants_delete(request, section_id=None):
    dest_url = reverse("admin:exp2_section_change", args=(section_id,))
    form = forms.BulkSectionParticipantsForm(request.POST)
    if form.is_valid():
        first_uid = form.cleaned_data["first_uid"]
        last_uid = form.cleaned_data["last_uid"]
        pre_existing_parts = get_pre_existing_participants(
            section_id, first_uid, last_uid)
        if len(pre_existing_parts) == (last_uid - first_uid) + 1:
            for part in pre_existing_parts:
                part.delete()
            add_success_message(request, first_uid, last_uid, "deleted")
            return HttpResponseRedirect(dest_url)
        else:
            err_msg = gen_missing_uids_error_message(
                first_uid, last_uid, pre_existing_parts)
            add_error_message(request, "Bulk Delete Form", err_msg)
    else:
        add_warning(request, "Bulk Delete Participants")
    delete_frm_set_init_vals(request)
    return HttpResponseRedirect(dest_url)

def detach_participant_from_user(request, participant_id):
    part = models.Participant.get(pk=participant_id)
    user = part.user
    user.participants.remove(part)
    user.save()
    part.user = None
    part.save()
    return HttpResponseRedirect(reverse('admin:exp2_participant_change',
                                        args=(participant_id,)))


def deploy_experiment(request, *args, **kwargs):
    exp_id = kwargs.get("experiment_id", None)
    deploy_files = request.POST.getlist("deploy_files", [])
    msgs = []
    for df in deploy_files:
        src = request.POST.get("src_%s" % df, None)
        dest = request.POST.get("dest_%s" % df, None)
        # print "%s %s %s" % (df, src, dest)
        msgs.append("%s" % os.path.basename(src))
    messages.info(request, " ".join(msgs))
    return HttpResponseRedirect(reverse('admin:tutalk_experiment_change',
                                        args=(exp_id,)))


def deploy_condition(request, *args, **kwargs):
    cond_id = kwargs.get("condition_id", None)
    deploy_files = request.POST.getlist("deploy_files", [])
    msgs = []
    for df in deploy_files:
        src = request.POST.get("src_%s" % df, None)
        dest = request.POST.get("dest_%s" % df, None)
        msgs.append("%s" % os.path.basename(src))
    messages.info(request, " ".join(msgs))
    return HttpResponseRedirect(reverse('admin:tutalk_condition_change',
                                        args=(cond_id,)))


def clone_experiment(request, *args, **kwargs):
    # collect params from kwargs and form
    exp_id = kwargs.get("experiment_id", None)
    exptr_id = request.POST.get("experimenter_id", None)
    new_exp_name = request.POST.get("experiment_name", "")
    scen_ids = request.POST.getlist("clone_scenarios", [])
    section_ids = request.POST.getlist("clone_sections", [])
    sec_ids = request.POST.getlist("clone_sections", [])
    sec_id_parts = request.POST.getlist("clone_section_participants", [])
    pretrain_task_ids = request.POST.getlist("clone_pretrain_tasks", [])
    posttrain_task_ids = request.POST.getlist("clone_posttrain_tasks", [])
    cond_ids = request.POST.getlist("clone_conditions", [])
    train_task_ids = request.POST.getlist("clone_condition_train_tasks", [])
    old_exp = models.Experiment.objects.get(pk=exp_id)
    new_exptr = models.Experimenter.objects.get(pk=exptr_id)
    # report error and re-draw form if they didn't enter a experiment name
    if "" == new_exp_name:
        messages.error(request, "You must specify a new experiment name")
        ctx = {
            'experiment': old_exp,
            'experimenters': models.Experimenter.objects.all()
        }
        return render(request, 'exp2/clone_experiment.html', ctx)
    # build up kwargs for exp.clone()
    scens = [models.Scenario.objects.get(pk=old_scen_id)
             for old_scen_id in scen_ids]
    sections = [models.section.objects.get(pk=old_st_id) for old_st_id in section_ids]
    secs = [models.Section.objects.get(pk=old_sec_id)
            for old_sec_id in sec_ids]
    conds = [models.Condition.objects.get(pk=old_cnd_id)
             for old_cnd_id in cond_ids]
    # Note: I would prefer to use a dict-comprehension but I don't think
    # that they can be used with a defaultdict
    cond_train_tasks = defaultdict(list)
    for cond_tt in train_task_ids:
        cond_id, tt_id = cond_tt.split('_')
        cond_train_tasks[int(cond_id)].append(
            models.TrainingTask.objects.get(pk=tt_id))
    pre_train_tasks = [models.PreTrainingTask.objects.get(pk=old_pre_id)
                       for old_pre_id in pretrain_task_ids]
    post_train_tasks = [models.PostTrainingTask.objects.get(pk=old_post_id)
                        for old_post_id in posttrain_task_ids]

    ctx = {
        'scenarios': scens,
        'conditions': conds,
        'condition_training_tasks': cond_train_tasks,
        'sections': sections,
        'sections': secs,
        'section_parts': sec_id_parts,
        'pre_training_tasks': pre_train_tasks,
        'post_training_tasks': post_train_tasks
    }
    # finally, clone the experiment
    new_exp = old_exp.clone(new_exptr, new_exp_name, **ctx)

    old_exp_fqn = "%s.%s" % (old_exp.experimenter.name, old_exp.name)
    new_exp_fqn = "%s.%s" % (new_exp.experimenter.name, new_exp.name)
    messages.info(request,
                  "%s cloned to %s" % (old_exp_fqn, new_exp_fqn))
    return HttpResponseRedirect(reverse('admin:tutalk_experimenter_change',
                                        args=(exptr_id)))


def clone_condition(request, *args, **kwargs):
    # collect params from kwargs and form
    cond_id = kwargs.get("condition_id", None)
    exp_id = request.POST.get("experiment_id", None)
    new_cond_name = request.POST.get("condition_name", "")
    train_task_ids = request.POST.getlist("clone_train_tasks", [])
    old_cond = models.Condition.objects.get(pk=cond_id)
    new_exp = models.Experiment.objects.get(pk=exp_id)
    # report error and re-draw form if they didn't enter a condition name
    # or if they kept the experiment the same and didn't change the name
    ctx = {
        'condition': old_cond,
        'experiments': models.Experiment.objects.all()
    }
    if "" == new_cond_name:
        messages.error(request, "You must specify a condition name")
        return render(request, 'exp2/clone_condition.html', ctx)
    if new_exp.id == old_cond.experiment.id and new_cond_name == old_cond.name:
        messages.error(request,
                       ("You must change the condition name if using the "
                        "same experiment"))
        return render(request, 'exp2/clone_condition.html', ctx)

    # build up kwargs for exp.clone()
    train_tasks = [models.TrainingTask.objects.get(pk=tt_id)
                   for tt_id in train_task_ids]

    # finally, clone the condition
    ctx = {'condition_name': new_cond_name}
    new_cond = old_cond.clone(new_exp, train_tasks, **ctx)

    old_cond_fqn = "%s.%s.%s" % (old_cond.experiment.experimenter.name,
                                 old_cond.experiment.name,
                                 old_cond.name)
    new_cond_fqn = "%s.%s.%s" % (new_cond.experiment.experimenter.name,
                                 new_cond.experiment.name,
                                 new_cond.name)
    messages.info(request,
                  "%s cloned to %s" % (old_cond_fqn, new_cond_fqn))
    return HttpResponseRedirect(reverse('admin:tutalk_experiment_change',
                                        args=(new_exp.id)))
