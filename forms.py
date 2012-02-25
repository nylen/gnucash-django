from django import forms

DEFAULT_OPPOSING_ACCOUNT_CHOICES = [('all', '(all)')]

class FilterForm(forms.Form):
  def __init__(self, choices, *args, **kwargs):
    super(FilterForm, self).__init__(*args, **kwargs)

    self.fields['opposing_accounts'] = forms.MultipleChoiceField(
      required=False, choices=choices, widget=forms.CheckboxSelectMultiple)

    self.fields['min_date'] = forms.DateField(
      required=False, initial='')
    self.fields['max_date'] = forms.DateField(
      required=False, initial='')
