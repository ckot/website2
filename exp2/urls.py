
from django.conf.urls import url, include
from . import views

urlpatterns = [
    url(r"^section/(?P<section_id>\d+)/bulk_add_change_participants",
        views.section_bulk_participants_add_change,
        name='bulk-add-change-participants'),

    url(r"^section/(?P<section_id>\d+)/bulk_delete_participants",
        views.section_bulk_participants_delete,
        name='bulk-delete-participants'),

    url(r"^experiment/(?P<experiment_id>\d+)/deploy/",
        views.deploy_experiment,
        name='deploy-experiment'),

    url(r"^experiment/(?P<experiment_id>\d+)/clone/",
        views.clone_experiment,
        name='clone-experiment'),

    url(r'^experiment/detach_participant_from_user/(?P<participant_id>\d+)',
        views.detach_participant_from_user,
        name='detach-participant-from-user'),

    url(r"^condition/(?P<condition_id>\d+)/deploy/",
        views.deploy_condition,
        name='deploy-condition'),

    url(r"^condition/(?P<condition_id>\d+)/clone/",
        views.clone_condition,
        name='clone-condition'),
]
