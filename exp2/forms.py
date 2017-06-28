
# from django.contrib import admin
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple

from .models import Experiment, Participant


class GetParentFormSet(forms.BaseInlineFormSet):
    def get_form_kwargs(self, index):
        kwargs = super(GetParentFormSet, self).get_form_kwargs(index)
        kwargs.update({'parent': self.instance})
        return kwargs


# class FacilityForm(forms.ModelForm):
#     pass

class SectionInlineForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        parent = kwargs.pop('parent')
        super(SectionInlineForm, self).__init__(*args, **kwargs)
        if self.instance.pk is None:
            parent_vals = self.instance.get_inherited_vals_from_parent(parent)
            for fld in parent_vals:
                self.fields[fld].initial = parent_vals[fld]
    class Meta:
        fields = ('name',
                  'pre_training_tasks_enabled',
                  'training_tasks_enabled',
                  'post_training_tasks_enabled')

# class ParticipantInlineForm(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         super(ParticipantInlineForm, self).__init__(*args, **kwargs)
#         print
#         print "BEFORE\n=================="
#         print self.fields
#         obj = self.instance
#         self.fields['uid'].value = obj.uid
#         self.fields['cond_name'].value = "None" if obj.condition is None else obj.condition.name
#         self.fields['assigned_to_user'].value = obj.user_id is not None
#         # print vars(obj)
#         print "\nAFTER\n=============="
#         print self.fields
#         print
#
#     def has_changed(self, *args, **kwargs):
#         if self.instance.pk is None:
#             # this is a new instance, inherit some attr vals from parent
#             # objects
#             # section-related attributes
#             section = self.instance.section
#             pre = section.pre_training_tasks_enabled
#             train = section.training_tasks_enabled
#             post = section.post_training_tasks_enabled
#             self.instance.pre_training_tasks_enabled = pre
#             self.instance.training_tasks_enabled = train
#             self.instance.post_training_tasks_enabled = post
#             cond = self.instance.condition
#             if cond is not None:
#                 # condition is selected, inherit some attr vals from condition
#                 etto = cond.enforce_training_task_order
#                 self.instance.enforce_training_task_order = etto
#             return True
#         return super(ParticipantInlineForm, self).has_changed(*args, **kwargs)
#
#     class Meta:
#         model = Participant
#         fields = ('uid', 'condition')


class BulkSectionParticipantsForm(forms.Form):
    error_css_class = 'error'
    required_css_class = 'required'
    first_uid = forms.IntegerField(required=True)
    last_uid = forms.IntegerField(required=True)

    def clean(self):
        cleaned_data = super(BulkSectionParticipantsForm, self).clean()
        first_uid = cleaned_data.get("first_uid")
        last_uid = cleaned_data.get("last_uid")
        if first_uid and last_uid and first_uid > last_uid:
            self.add_error(None, "first_uid greater than last_uid")
        return cleaned_data


class BulkParticipantConditionsForm(BulkSectionParticipantsForm):
    ACTION_CHOICES = [
        ('', ''),
        ('create', 'Create'),
        ('update', 'Update')
    ]
    action = forms.ChoiceField(label="Condition Mapping order",
                               required=True,
                               choices=ACTION_CHOICES)

    def __init__(self, *args, **kwargs):
        """adds conditions fld and it's choices using kwargs to build queryset

        kwargs["exp_id"] must be passed. it's immediately popped off of
        kwargs so that super().__init__() can be called as close to the top
        of the method as possible
        """
        # pylint: disable=I0011,E1101
        exp = Experiment.objects.get(pk=kwargs.pop("exp_id"))
        super(BulkParticipantConditionsForm, self).__init__(*args, **kwargs)
        self.fields['conditions'] = \
            forms.ModelMultipleChoiceField(
                queryset=exp.conditions.all(),
                required=True,
                widget=FilteredSelectMultiple("Conditions",
                                              is_stacked=False,
                                              attrs={"size": 5}))
