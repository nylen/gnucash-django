from django.contrib.auth.decorators import login_required
from django.core.paginator          import Paginator, EmptyPage, PageNotAnInteger
from django.http                    import HttpResponse
from django.template                import RequestContext, loader

from gnucash_data.models            import Account, Split, Lock

import json

import filters
import forms
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

  modify_form = forms.ModifyForm(choices, request.GET, auto_id="modify_id_%s")

  try:
    page_num = int(request.GET.get('page'))
  except:
    page_num = 1

  items_per_page = 50
  pages = Paginator(splits.filtered_splits, items_per_page)

  try:
    page = pages.page(page_num)
  except PageNotAnInteger:
    page = pages.page(1)
  except EmptyPage:
    page = pages.page(pages.num_pages)

  c = RequestContext(request, {
    'any_filters_applied': splits.any_filters_applied,
    'opposing_account_filter_applied': splits.opposing_account_filter_applied,
    'regex_chars_js': json.dumps(filters.TransactionSplitFilter.REGEX_CHARS),
    'accounts_js': json.dumps(choices.accounts_dict),
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

  choices = forms.AccountChoices(account)

  opposing_account_guid = request.POST['change_opposing_account']
  opposing_account = Account.objects.get(guid=opposing_account_guid)

  filter_form = forms.HiddenFilterForm(choices, request.POST)
  if filter_form.is_valid():
    splits.filter_splits(filter_form.cleaned_data)

  form_data = request.POST.copy()

  modified_transactions = False

  tx_count = splits.filtered_splits.count()
  if tx_count > 0:
    tx_guids = splits.filtered_splits.distinct().values('transaction__guid')
    split_guids = list(Split.objects.filter(transaction__guid__in=tx_guids)
      .exclude(account=account).values_list('guid', flat=True))

    Lock.obtain()
    Split.objects.filter(guid__in=split_guids).update(account=opposing_account)
    Lock.release()

    form_data['opposing_accounts'] = opposing_account_guid

    modified_transactions = True

  hidden_filter_form = forms.HiddenFilterForm(choices, form_data)

  c = RequestContext(request, {
    'account': account,
    'opposing_account': opposing_account,
    'hidden_filter_form': hidden_filter_form,
    'modified_transactions': modified_transactions,
    'tx_count': tx_count,
  })
  return HttpResponse(template.render(c))
