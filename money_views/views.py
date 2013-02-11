import json

from django.contrib.auth.decorators import login_required
from django.core.paginator          import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers       import reverse
from django.http                    import HttpResponse
from django.shortcuts               import redirect
from django.template                import RequestContext, loader

import api
import filters
import forms
import settings
from gnucash_data.models import Account, Transaction


def get_account(key):
  try:
    path = settings.ACCOUNTS_LIST[int(key)]
    return Account.from_path(path)
  except ValueError:
    return Account.get(key)


@login_required
def index(request):
  template = loader.get_template('page_index.html')
  accounts = [Account.from_path(path) for path in settings.ACCOUNTS_LIST]

  all_accounts = Account.get_all()
  all_accounts.sort(key=lambda a: a.path)

  c = RequestContext(request, {
    'accounts': accounts,
    'all_accounts': all_accounts,
    'showing_index': True,
  })
  return HttpResponse(template.render(c))


@login_required
def any_account(request):
  key = request.GET.get('select_account', '')
  if key:
    return redirect(reverse(
      'money_views.views.account',
      kwargs={'key': request.GET.get('select_account', '')}))
  else:
    return redirect('money_views.views.index')


@login_required
def account(request, key):
  template = loader.get_template('page_account_details.html')

  account = get_account(key)
  splits = filters.TransactionSplitFilter(account)

  all_accounts = Account.get_all()
  all_accounts.sort(key=lambda a: a.path)
  all_accounts_dict = {}
  for a in all_accounts:
    all_accounts_dict[a.guid] = {
      'path': a.path,
      'name': a.name
    }

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

  Transaction.cache_from_splits(page.object_list)

  c = RequestContext(request, {
    'any_filters_applied': splits.any_filters_applied,
    'one_opposing_account_filter_applied': splits.one_opposing_account_filter_applied,
    'regex_chars_js': json.dumps(filters.TransactionSplitFilter.REGEX_CHARS),
    'all_accounts': all_accounts,
    'accounts_js': json.dumps(all_accounts_dict),
    'current_account_js': json.dumps(account.guid),
    'num_transactions_js': json.dumps(page.paginator.count),
    'api_functions_js': json.dumps(api.function_urls.urls_dict),
    'account': account,
    'page': page,
    'filter_form': filter_form,
    'modify_form': modify_form,
  })
  return HttpResponse(template.render(c))


@login_required
def modify(request, key):
  template = loader.get_template('page_modify.html')

  account = get_account(key)
  splits = filters.TransactionSplitFilter(account)

  errors = False

  choices = forms.AccountChoices(account)

  opposing_account_guid = request.POST['change_opposing_account']
  opposing_account = None
  try:
    opposing_account = Account.get(opposing_account_guid)
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
def batch_categorize(request, key):
  template = loader.get_template('page_batch_categorize.html')

  account = get_account(key)
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
def apply_categorize(request, key):
  template = loader.get_template('page_apply_categorize.html')

  account = get_account(key)
  splits = filters.TransactionSplitFilter(account)

  imbalance = Account.from_path('Imbalance-USD')
  choices = forms.AccountChoices(account, exclude=imbalance)

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
          opposing_account=Account.get(opposing_account_guid),
          save_rule=True)

  c = RequestContext(request, {
    'account': account,
    'modified_tx_count': modified_tx_count,
    'rule_count': rule_count,
  })
  return HttpResponse(template.render(c))
