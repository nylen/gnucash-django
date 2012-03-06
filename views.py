from django.contrib.auth.decorators import login_required
from django.core.paginator          import Paginator, EmptyPage, PageNotAnInteger
from django.db.models               import F, Q
from django.http                    import HttpResponse
from django.template                import RequestContext, loader

from gnucash_data.models            import Account, Split, Lock, Rule, RuleAccount

from decimal import Decimal

import json

import filters
import forms
import re
import settings


@login_required
def index(request):
  template = loader.get_template('index.html')
  accounts = [Account.from_path(path) for path in settings.ACCOUNTS_LIST]

  c = RequestContext(request, {
    'accounts': accounts,
    'show_account_links': True,
  })
  return HttpResponse(template.render(c))


@login_required
def account(request, index):
  template = loader.get_template('account_details.html')

  path = settings.ACCOUNTS_LIST[int(index)]
  account = Account.from_path(path)
  splits = filters.TransactionSplitFilter(account)

  choices = forms.AccountChoices(account)

  filter_form = forms.FilterForm(choices, request.GET)
  if filter_form.is_valid():
    splits.filter_splits(filter_form.cleaned_data)

  splits.order_filtered_splits()

  modify_form_data = request.GET.copy()
  modify_form_data['save_rule'] = True
  modify_form = forms.ModifyForm(choices, modify_form_data, auto_id="modify_id_%s")

  try:
    page_num = int(request.GET.get('page'))
  except:
    page_num = 1

  pages = Paginator(splits.filtered_splits, settings.NUM_TRANSACTIONS_PER_PAGE)

  try:
    page = pages.page(page_num)
  except PageNotAnInteger:
    page = pages.page(1)
  except EmptyPage:
    page = pages.page(pages.num_pages)

  c = RequestContext(request, {
    'any_filters_applied': splits.any_filters_applied,
    'one_opposing_account_filter_applied': splits.one_opposing_account_filter_applied,
    'regex_chars_js': json.dumps(filters.TransactionSplitFilter.REGEX_CHARS),
    'accounts_js': json.dumps(choices.accounts_dict),
    'num_transactions_js': json.dumps(page.paginator.count),
    'account': account,
    'page': page,
    'filter_form': filter_form,
    'modify_form': modify_form,
  })
  return HttpResponse(template.render(c))


@login_required
def modify(request, index):
  template = loader.get_template('modify.html')

  path = settings.ACCOUNTS_LIST[int(index)]
  account = Account.from_path(path)
  splits = filters.TransactionSplitFilter(account)

  errors = False

  choices = forms.AccountChoices(account)

  opposing_account_guid = request.POST['change_opposing_account']
  opposing_account = None
  try:
    opposing_account = Account.objects.get(guid=opposing_account_guid)
  except Account.DoesNotExist:
    errors = "Account '%s' not found." % opposing_account_guid

  form_data = request.POST.copy()

  modified_tx_count = 0

  if not errors:
    modify_form = forms.ModifyForm(choices, request.POST)
    if modify_form.is_valid():
      splits.filter_splits(modify_form.cleaned_data)

      save_rule = modify_form.cleaned_data['save_rule']
      if save_rule and not splits.tx_desc:
        errors = 'Cannot save rule with no description filter.'
        save_rule = False

      modified_tx_count = filters.RuleHelper.apply(
        splits=splits,
        opposing_account=opposing_account,
        min_amount=modify_form.cleaned_data['min_amount'],
        max_amount=modify_form.cleaned_data['max_amount'],
        save_rule=save_rule)

      if modified_tx_count:
        form_data['opposing_accounts'] = opposing_account_guid

    else:
      # modify_form is not valid
      errors = str(modify_form.errors)

  hidden_filter_form = forms.HiddenFilterForm(choices, form_data)

  c = RequestContext(request, {
    'account': account,
    'opposing_account': opposing_account,
    'hidden_filter_form': hidden_filter_form,
    'errors': errors,
    'modified_tx_count': modified_tx_count,
  })
  return HttpResponse(template.render(c))


@login_required
def batch_categorize(request, index):
  template = loader.get_template('batch_categorize.html')

  path = settings.ACCOUNTS_LIST[int(index)]
  account = Account.from_path(path)
  splits = filters.TransactionSplitFilter(account)

  imbalance = Account.from_path('Imbalance-USD')
  choices = forms.AccountChoices(account, exclude=imbalance)

  merchants = splits.get_merchants_info(imbalance)
  no_merchants = (len(merchants) == 0)
  batch_modify_form = forms.BatchModifyForm(choices, merchants)

  c = RequestContext(request, {
    'account': account,
    'batch_modify_form': batch_modify_form,
    'no_merchants': no_merchants,
    'imbalance': imbalance,
  })
  return HttpResponse(template.render(c))


@login_required
def apply_categorize(request, index):
  template = loader.get_template('apply_categorize.html')

  path = settings.ACCOUNTS_LIST[int(index)]
  account = Account.from_path(path)
  imbalance = Account.from_path('Imbalance-USD')

  choices = forms.AccountChoices(account, exclude=imbalance)

  splits = filters.TransactionSplitFilter(account)
  merchants = splits.get_merchants_info(imbalance)
  batch_modify_form = forms.BatchModifyForm(choices, merchants, request.POST)

  if not batch_modify_form.is_valid():
    raise ValueError(batch_modify_form.errors)

  modified_tx_count = 0
  rule_count = 0

  for i in range(settings.NUM_MERCHANTS_BATCH_CATEGORIZE):
    if 'merchant_' + str(i) in batch_modify_form.cleaned_data:
      tx_desc = batch_modify_form.cleaned_data['merchant_name_' + str(i)]
      opposing_account_guid = batch_modify_form.cleaned_data['merchant_' + str(i)]
      if opposing_account_guid:
        rule_count += 1
        modified_tx_count += filters.RuleHelper.apply(
          splits=splits,
          tx_desc=tx_desc,
          opposing_account=Account.objects.get(guid=opposing_account_guid),
          save_rule=True)

  c = RequestContext(request, {
    'account': account,
    'modified_tx_count': modified_tx_count,
    'rule_count': rule_count,
  })
  return HttpResponse(template.render(c))
