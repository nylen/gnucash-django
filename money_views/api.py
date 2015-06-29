import json

from django.core.urlresolvers import reverse, NoReverseMatch
from django.http              import HttpResponse, HttpResponseForbidden

import filters
import forms

from gnucash_data.models import Split, Lock, Account, Transaction
from utils               import misc_functions


class ApiFunctionUrls():
  def __init__(self):
    self.functions = []
    self._urls_dict = None

  def register_function(self, func):
    self.functions.append(func)

  @property
  def urls_dict(self):
    if self._urls_dict is None:
      self._urls_dict = {}
      for func in self.functions:
        self._urls_dict[func.__name__] = \
          reverse(__name__ + '.' + func.__name__)
    return self._urls_dict

function_urls = ApiFunctionUrls()


def json_api_function(func):
  function_urls.register_function(func)
  def helper(request, *args, **kwargs):
    try:
      if not request.user.is_authenticated():
        return HttpResponseForbidden(
          'User is not authenticated.  Refresh the page and try again.')
      data = json.dumps(func(request, *args, **kwargs))
    except Exception, e:
      data = json.dumps({'error': 'Error: ' + str(e)})
    return HttpResponse(data, mimetype='application/json')
  return helper


@json_api_function
def change_memo(request):
  split_guid = request.POST.get('split_guid', '')
  memo = request.POST.get('memo', '')
  split = Split.objects.get(guid=split_guid)
  Lock.obtain()
  try:
    split.memo = request.POST.get('memo', '')
    split.save()
  finally:
    Lock.release()
  return {
    'split_guid': split_guid,
    'memo': memo,
  }


@json_api_function
def change_account(request):
  split_guid = request.POST.get('split_guid', '')
  account_guid = request.POST.get('account_guid', '')
  split = Split.objects.get(guid=split_guid)
  Lock.obtain()
  try:
    split.account = Account.objects.get(guid=account_guid)
    split.save()
  finally:
    Lock.release()
  return {
    'split_guid': split_guid,
    'account_guid': account_guid,
  }


@json_api_function
def get_transactions(request):
  # This is not structured like the other account views (with a `key` parameter
  # in the URL) because the code above that builds _urls_dict cannot handle
  # views with parameters.
  key = request.GET.get('accounts')

  accounts = misc_functions.get_accounts_by_webapp_key(key)
  splits = filters.TransactionSplitFilter(accounts)

  choices = forms.AccountChoices(accounts)

  filter_form = forms.FilterForm(choices, request.GET)
  if filter_form.is_valid():
    splits.filter_splits(filter_form.cleaned_data)

  splits.order_filtered_splits()

  Transaction.cache_from_splits(splits.filtered_splits)
  data_splits = []
  data_transactions = []
  transactions_seen = {}

  for s in splits.filtered_splits:
    # Determine the best memo to show, if any
    # TODO logic duplicated with money_views.views.account_csv
    memo = ''
    if s.memo_is_id_or_blank:
      for memo_split in s.opposing_split_set:
        if not memo_split.memo_is_id_or_blank:
          memo = memo_split.memo
          break
    else:
      memo = s.memo

    tx = s.transaction

    if tx.guid not in transactions_seen:
      data_tx_splits = []
      for ts in tx.split_set.all():
        data_tx_splits.append({
          'guid': ts.guid,
          'account': {
            'friendly_name': ts.account.description_or_name,
            'path': ts.account.path,
            'guid': ts.account.guid
          },
          'memo': ts.memo,
          'amount': str(ts.amount)
        })
      data_transactions.append({
        'guid': tx.guid,
        'description': tx.description,
        'post_date': misc_functions.date_to_timestamp(tx.post_date),
        'splits': data_tx_splits
      })
      transactions_seen[tx.guid] = True

    opposing_account = s.opposing_account
    data_splits.append({
      'account': {
        'friendly_name': s.account.description_or_name,
        'path': s.account.path,
        'guid': s.account.guid
      },
      'opposing_account': {
        'friendly_name': opposing_account.description_or_name,
        'path': opposing_account.path,
        'guid': opposing_account.guid
      },
      'tx_guid': tx.guid,
      'description': tx.description,
      'memo': memo,
      'post_date': misc_functions.date_to_timestamp(tx.post_date),
      'amount': str(s.amount)
    })

  return {
    'splits': data_splits,
    'transactions': data_transactions
  }
