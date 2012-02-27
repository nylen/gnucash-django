from django import forms

DEFAULT_OPPOSING_ACCOUNT_CHOICES = [('all', '(all)')]
DEFAULT_CHANGE_ACCOUNT_CHOICES = [('', '(no change)')]

class FilterForm(forms.Form):
  def __init__(self, accounts, *args, **kwargs):
    super(FilterForm, self).__init__(*args, **kwargs)

    self.fields['opposing_accounts'] = forms.MultipleChoiceField(
      required=False, choices=accounts, widget=forms.CheckboxSelectMultiple)

    self.fields['tx_desc'] = forms.CharField(
      required=False, initial='', label='Description')
    self.fields['min_date'] = forms.DateField(
      required=False, initial='')
    self.fields['max_date'] = forms.DateField(
      required=False, initial='')

class ModifyForm(FilterForm):
  def __init__(self, accounts, filter_accounts, *args, **kwargs):
    super(ModifyForm, self).__init__(filter_accounts, *args, **kwargs)

    self.fields['opposing_accounts'].widget = forms.MultipleHiddenInput()
    self.fields['min_date'].widget = forms.HiddenInput()
    self.fields['max_date'].widget = forms.HiddenInput()
    for a in ['readonly', 'class']:
      self.fields['tx_desc'].widget.attrs[a] = 'readonly'

    self.fields['change_opposing_account'] = forms.ChoiceField(
      required=False, initial='', choices=accounts)

    self.fields['min_amount'] = forms.IntegerField(
      required=False, initial='')
    self.fields['max_amount'] = forms.IntegerField(
      required=False, initial='')
    self.fields['save_rule'] = forms.BooleanField(
      required=False, initial=False,
      label='Save rule for future transactions')

class HiddenFilterForm(FilterForm):
  def __init__(self, accounts, *args, **kwargs):
    super(HiddenFilterForm, self).__init__(accounts, *args, **kwargs)

    self.fields['opposing_accounts'].widget = forms.MultipleHiddenInput()
    self.fields['min_date'].widget = forms.HiddenInput()
    self.fields['max_date'].widget = forms.HiddenInput()
    self.fields['tx_desc'].widget = forms.HiddenInput()
