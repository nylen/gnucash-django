from django    import forms
from django.db import connections


DEFAULT_FILTER_ACCOUNT_CHOICES = [('all', '(all)')]
DEFAULT_MODIFY_ACCOUNT_CHOICES = [('', '(no change)')]


class FilterForm(forms.Form):
  def __init__(self, choices, *args, **kwargs):
    super(FilterForm, self).__init__(*args, **kwargs)

    self.fields['opposing_accounts'] = forms.MultipleChoiceField(
      required=False, choices=choices.filter_account_choices,
      widget=forms.CheckboxSelectMultiple)

    self.fields['tx_desc'] = forms.CharField(
      required=False, initial='', label='Description')
    self.fields['min_date'] = forms.DateField(
      required=False, initial='')
    self.fields['max_date'] = forms.DateField(
      required=False, initial='')


class ModifyForm(FilterForm):
  def __init__(self, choices, *args, **kwargs):
    super(ModifyForm, self).__init__(choices, *args, **kwargs)

    self.fields['opposing_accounts'].widget = forms.MultipleHiddenInput()
    self.fields['min_date'].widget = forms.HiddenInput()
    self.fields['max_date'].widget = forms.HiddenInput()
    for a in ['readonly', 'class']:
      self.fields['tx_desc'].widget.attrs[a] = 'readonly'

    self.fields['change_opposing_account'] = forms.ChoiceField(
      required=False, initial='', choices=choices.modify_account_choices)

    self.fields['min_amount'] = forms.DecimalField(
      required=False, initial='')
    self.fields['max_amount'] = forms.DecimalField(
      required=False, initial='')
    self.fields['save_rule'] = forms.BooleanField(
      required=False, initial=True,
      label='Save rule for future transactions')


class HiddenFilterForm(FilterForm):
  def __init__(self, choices, *args, **kwargs):
    super(HiddenFilterForm, self).__init__(choices, *args, **kwargs)

    self.fields['opposing_accounts'].widget = forms.MultipleHiddenInput()
    self.fields['opposing_accounts'].choices = choices.filter_all_account_choices
    self.fields['min_date'].widget = forms.HiddenInput()
    self.fields['max_date'].widget = forms.HiddenInput()
    self.fields['tx_desc'].widget = forms.HiddenInput()


class BatchModifyForm(forms.Form):
  def __init__(self, choices, merchants, *args, **kwargs):
    super(BatchModifyForm, self).__init__(*args, **kwargs)

    for merchant in merchants:
      field = forms.ChoiceField(
        required=False, initial='', choices=choices.modify_account_choices)
      field.merchant_info = merchant
      self.fields[merchant['html_name']] = field
      self.fields[merchant['ref_html_name']] = forms.CharField(
        initial=merchant['description'], widget=forms.HiddenInput)


class AccountChoices():
  def __init__(self, account, **kwargs):
    cursor = connections['gnucash'].cursor()
    cursor.execute('''
        SELECT a.guid, a.name, a.parent_guid,

          CASE
            WHEN s.account_guid IS NULL THEN 0
            ELSE 1
          END AS is_present,

          a.placeholder

        FROM accounts a

        LEFT JOIN (
          SELECT s2.account_guid,
            MAX(t.post_date) post_date

          FROM splits s

          INNER JOIN transactions t
          ON s.tx_guid = t.guid

          INNER JOIN splits s2
          ON s2.tx_guid = t.guid

          WHERE s.account_guid = %s
          AND s2.account_guid <> %s

          GROUP BY 1
        ) s
        ON s.account_guid = a.guid

        WHERE a.account_type <> 'ROOT'
      ''', [account.guid, account.guid])

    accounts_dict = {}

    filter_all_account_choices = []
    filter_account_choices = []
    modify_account_choices = []

    for row in cursor.fetchall():
      filter_all_account_choices.append((row[0], row[1]))
      if row[3]:
        filter_account_choices.append((row[0], row[1]))
      accounts_dict[row[0]] = {
        'name': row[1],
        'parent_guid': row[2],
        'placeholder': row[4],
      }

    for guid, a in accounts_dict.items():
      if not a['placeholder']:
        path_list = [a['name']]
        parent_guid = a['parent_guid']
        while parent_guid in accounts_dict:
          path_list.append(accounts_dict[parent_guid]['name'])
          parent_guid = accounts_dict[parent_guid]['parent_guid']
        path_list.reverse()
        a['path'] = ':'.join(path_list)
        if guid != account.guid:
          if 'exclude' not in kwargs or guid != kwargs['exclude'].guid:
            modify_account_choices.append((guid, a['path']))

    get_account_path = lambda a: accounts_dict[a[0]]['path']
    filter_account_choices.sort(key=get_account_path)
    modify_account_choices.sort(key=get_account_path)

    self.accounts_dict = accounts_dict

    self.filter_all_account_choices = \
      DEFAULT_FILTER_ACCOUNT_CHOICES + filter_all_account_choices
    self.filter_account_choices = \
      DEFAULT_FILTER_ACCOUNT_CHOICES + filter_account_choices
    self.modify_account_choices = \
      DEFAULT_MODIFY_ACCOUNT_CHOICES + modify_account_choices
