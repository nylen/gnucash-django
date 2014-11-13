from dateutil import parser as dateparser
from decimal import Decimal
import json
import os

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
from gnucash_data.models import Account, Lock, Transaction


set_home_for_gnucash_api = False


def get_accounts(key):
  return [get_account(k) for k in key.split('+')]

def get_account(key):
  try:
    path = settings.ACCOUNTS_LIST[int(key)]
    return Account.from_path(path)
  except ValueError:
    return Account.get(key)

def accounts_key(accounts):
  return '+'.join(a.webapp_key for a in accounts)


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
  key = request.GET.getlist('accounts')
  if len(key):
    return redirect(reverse(
      'money_views.views.account',
      kwargs={'key': '+'.join(key)}))
  else:
    return redirect('money_views.views.index')


@login_required
def account(request, key):
  template = loader.get_template('page_account_details.html')

  accounts = get_accounts(key)
  splits = filters.TransactionSplitFilter(accounts)

  all_accounts = Account.get_all()
  all_accounts.sort(key=lambda a: a.path)
  all_accounts_dict = {}
  for a in all_accounts:
    all_accounts_dict[a.guid] = {
      'path': a.path,
      'name': a.name
    }

  choices = forms.AccountChoices(accounts)

  filter_form = forms.FilterForm(choices, request.GET)
  if filter_form.is_valid():
    splits.filter_splits(filter_form.cleaned_data)

  splits.order_filtered_splits()

  modify_form_data = request.GET.copy()
  modify_form_data['save_rule'] = True
  modify_form = forms.ModifyForm(choices, modify_form_data, auto_id="modify_id_%s")

  try:
    can_add_transactions = settings.ENABLE_ADD_TRANSACTIONS
  except AttributeError:
    can_add_transactions = False

  can_add_transactions = (can_add_transactions and len(accounts) == 1)

  if can_add_transactions:
    new_transaction_form = forms.NewTransactionForm(choices, auto_id='id_new_trans_%s')
  else:
    new_transaction_form = None

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
    'current_accounts_js': json.dumps([a.guid for a in accounts]),
    'num_transactions_js': json.dumps(page.paginator.count),
    'api_functions_js': json.dumps(api.function_urls.urls_dict),
    'accounts': accounts,
    'current_accounts_key': accounts_key(accounts),
    'can_add_transactions': can_add_transactions,
    'account': accounts[0],
    'page': page,
    'filter_form': filter_form,
    'modify_form': modify_form,
    'new_transaction_form': new_transaction_form,
    'total_balance': sum(a.balance for a in accounts),
  })
  return HttpResponse(template.render(c))


@login_required
def account_csv(request, key):
  accounts = get_accounts(key)
  splits = filters.TransactionSplitFilter(accounts)

  choices = forms.AccountChoices(accounts)

  filter_form = forms.FilterForm(choices, request.GET)
  if filter_form.is_valid():
    splits.filter_splits(filter_form.cleaned_data)

  splits.order_filtered_splits()

  if 'inline' in request.GET:
    res = HttpResponse(content_type='text/plain')
  else:
    res = HttpResponse(content_type='text/csv')
    res['Content-Disposition'] = 'attachment; filename=accounts.csv'

  res.write('Account,OpposingAccount,Date,Description,Memo,Amount\n')

  for s in splits.filtered_splits:
    # Determine the best memo to show, if any
    memo = ''
    if s.memo_is_id_or_blank:
      for memo_split in s.opposing_split_set:
        if not memo_split.memo_is_id_or_blank:
          memo = memo_split.memo
          break
    else:
      memo = s.memo
    # Send CSV row
    res.write(','.join(f.replace(',', ';').replace('"', '').replace('\n', ' ') for f in [
      s.account.description_or_name,
      s.opposing_account.description_or_name,
      s.transaction.post_date.strftime('%m/%d/%Y'),
      s.transaction.description,
      memo,
      str(s.amount)
    ]) + '\n')

  return res


@login_required
def modify(request, key):
  template = loader.get_template('page_modify.html')

  accounts = get_accounts(key)
  splits = filters.TransactionSplitFilter(accounts)

  errors = False

  choices = forms.AccountChoices(accounts)

  opposing_account_guid = request.POST['change_opposing_account']
  opposing_account = None
  try:
    if opposing_account_guid != 'DELETE':
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
    'accounts': accounts,
    'current_accounts_key': accounts_key(accounts),
    'opposing_account': opposing_account,
    'hidden_filter_form': hidden_filter_form,
    'errors': errors,
    'modified_tx_count': modified_tx_count,
  })
  return HttpResponse(template.render(c))


@login_required
def batch_categorize(request, key):
  template = loader.get_template('page_batch_categorize.html')

  accounts = get_accounts(key)
  splits = filters.TransactionSplitFilter(accounts)

  imbalance = Account.from_path('Imbalance-USD')
  choices = forms.AccountChoices(accounts, exclude=imbalance)

  merchants = splits.get_merchants_info(imbalance)
  no_merchants = (len(merchants) == 0)
  batch_modify_form = forms.BatchModifyForm(choices, merchants)

  c = RequestContext(request, {
    'accounts': accounts,
    'current_accounts_key': accounts_key(accounts),
    'batch_modify_form': batch_modify_form,
    'no_merchants': no_merchants,
    'imbalance': imbalance,
  })
  return HttpResponse(template.render(c))


@login_required
def apply_categorize(request, key):
  template = loader.get_template('page_apply_categorize.html')

  accounts = get_accounts(key)
  splits = filters.TransactionSplitFilter(accounts)

  imbalance = Account.from_path('Imbalance-USD')
  choices = forms.AccountChoices(accounts, exclude=imbalance)

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
        opposing_account = None
        if opposing_account_guid != 'DELETE':
          opposing_account = Account.get(opposing_account_guid)
        modified_tx_count += filters.RuleHelper.apply(
          splits=splits,
          tx_desc=tx_desc,
          opposing_account=opposing_account,
          save_rule=True)

  c = RequestContext(request, {
    'accounts': accounts,
    'current_accounts_key': accounts_key(accounts),
    'modified_tx_count': modified_tx_count,
    'rule_count': rule_count,
  })
  return HttpResponse(template.render(c))


@login_required
def new_transaction(request, key):
  accounts = get_accounts(key)
  if len(accounts) != 1:
    raise ValueError('Can only create transactions for 1 account at a time.')
  src_account = accounts[0]

  choices = forms.AccountChoices(accounts)

  new_tx_form = forms.NewTransactionForm(choices, request.POST)

  if not new_tx_form.is_valid():
    raise ValueError(new_tx_form.errors)

  txinfo = new_tx_form.cleaned_data

  txinfo['amount'] = Decimal(txinfo['amount'])

  global set_home_for_gnucash_api
  if not set_home_for_gnucash_api:
    # Bad gnucash depends on $HOME (this dir needs to be writable by the webserver)
    os.environ['HOME'] = os.path.abspath(os.path.join(
      os.path.dirname(os.path.dirname(__file__)), 'gnucash_api_home'))
    set_home_for_gnucash_api = True

  import gnucash
  from gnucash_scripts import common

  # make sure we can begin a session
  Lock.check_can_obtain()

  # begin GnuCash API session
  session = gnucash.Session(settings.GNUCASH_CONN_STRING)

  try:
    book = session.book
    USD = book.get_table().lookup('ISO4217', 'USD')

    root = book.get_root_account()
    imbalance = common.get_account_by_path(root, 'Imbalance-USD')

    acct = common.get_account_by_guid(root, src_account.guid)
    opposing_acct = common.get_account_by_guid(root, txinfo['opposing_account'])
    gnc_amount = common.decimal_to_gnc_numeric(Decimal(txinfo['amount']))

    # From example script 'test_imbalance_transaction.py'
    trans = gnucash.Transaction(book)
    trans.BeginEdit()
    trans.SetCurrency(USD)
    trans.SetDescription(str(txinfo['tx_desc']))
    trans.SetDate(
      txinfo['post_date'].day,
      txinfo['post_date'].month,
      txinfo['post_date'].year)

    split1 = gnucash.Split(book)
    split1.SetParent(trans)
    split1.SetAccount(acct)
    if txinfo.has_key('memo'):
      split1.SetMemo(str(txinfo['memo']))
    # The docs say both of these are needed:
    # http://svn.gnucash.org/docs/HEAD/group__Transaction.html
    split1.SetValue(gnc_amount)
    split1.SetAmount(gnc_amount)
    split1.SetReconcile('c')

    if opposing_acct != None:
      split2 = gnucash.Split(book)
      split2.SetParent(trans)
      split2.SetAccount(opposing_acct)
      split2.SetValue(gnc_amount.neg())
      split2.SetAmount(gnc_amount.neg())
      split2.SetReconcile('c')

    trans.CommitEdit()

  finally:
    session.end()
    session.destroy()

  return redirect(reverse(
    'money_views.views.account',
    kwargs={'key': key}))


@login_required
def transaction_files(request, guid):
  template = loader.get_template('page_txaction_files.html')
  transaction = Transaction.objects.get(guid=guid)

  c = RequestContext(request, {
    'transaction': transaction
  })
  return HttpResponse(template.render(c))


@login_required
def transaction_upload_file(request, guid):
  f = request.FILES.get('file')
  if f:
    Transaction.objects.get(guid=guid).attach_file(f)
  return redirect(reverse(
    'money_views.views.transaction_files',
    kwargs={'guid': guid}))


@login_required
def transaction_delete_file(request, guid, hash):
  Transaction.objects.get(guid=guid).file_set.filter(hash=hash).delete()
  return redirect(reverse(
    'money_views.views.transaction_files',
    kwargs={'guid': guid}))
