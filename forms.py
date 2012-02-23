from django import forms

DEFAULT_OPPOSING_ACCOUNT_CHOICES = [('', '(all)')]

class FilterForm(forms.Form):
  opposing_account = forms.ChoiceField(
    required=False, choices=DEFAULT_OPPOSING_ACCOUNT_CHOICES)
  min_date = forms.DateField(
    required=False, initial='')
  max_date = forms.DateField(
    required=False, initial='')
