from django.contrib.auth.decorators import login_required
from django.core.paginator          import Paginator, EmptyPage, PageNotAnInteger
from django.db                      import connections
from django.db.models               import F
from django.http                    import HttpResponse
from django.template                import RequestContext, loader

from gnucash_data.models            import Account, Split, Lock
from utils.misc_functions           import utc_to_local

import datetime
import json

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

  items_per_page = 50

  splits = account.split_set.select_related(depth=3)

  filtering_any = False
  filtering_opposing_accounts = False
  tx_desc = ''
  regex_chars = '^$()[]?*+|\\'

  choices = forms.AccountChoices(account)

  filter_form = forms.FilterForm(choices, request.GET)

  if filter_form.is_valid():

    opposing_account_guids = filter_form.cleaned_data['opposing_accounts']
    if opposing_account_guids and 'all' not in opposing_account_guids:
      filtering_any = True
      filtering_opposing_accounts = True
      splits = splits.filter(transaction__split__account__guid__in=opposing_account_guids)

    tx_desc = filter_form.cleaned_data['tx_desc']
    if tx_desc:
      filtering_any = True
      if True in (c in tx_desc for c in regex_chars):
        splits = splits.filter(transaction__description__iregex=tx_desc)
      else:
        splits = splits.filter(transaction__description__icontains=tx_desc)

    min_date = filter_form.cleaned_data['min_date']
    if min_date:
      filtering_any = True
      splits = splits.filter(transaction__post_date__gte=min_date)
      min_date = splits.count()

    max_date = filter_form.cleaned_data['max_date']
    if max_date:
      filtering_any = True
      # Yes, this is weird.  No, it doesn't work otherwise.
      splits = splits.filter(transaction__post_date__lt=max_date + datetime.timedelta(days=1))
      max_date = splits.count()


  modify_form = forms.ModifyForm(choices, request.GET, auto_id="modify_id_%s")


  splits = splits.order_by(
    'transaction__post_date',
    'transaction__enter_date',
    'guid').reverse()

  try:
    page_num = int(request.GET.get('page'))
  except:
    page_num = 1

  pages = Paginator(splits, items_per_page)

  try:
    page = pages.page(page_num)
  except PageNotAnInteger:
    page = pages.page(1)
  except EmptyPage:
    page = pages.page(pages.num_pages)

  c = RequestContext(request, {
    'filtering_any': filtering_any,
    'filtering_opposing_accounts': filtering_opposing_accounts,
    'tx_desc': tx_desc,
    'regex_chars_js': json.dumps(regex_chars),
    'accounts_js': json.dumps(choices.accounts_dict),
    'account': account,
    'page': page,
    'filter_form': filter_form,
    'modify_form': modify_form,
  })
  return HttpResponse(template.render(c))


@login_required
def modify(request, index):
  path = settings.ACCOUNTS_LIST[int(index)]
  account = Account.from_path(path)

  template = loader.get_template('modify.html')

  lock = Lock.obtain()

  choices = forms.AccountChoices(account)

  # TODO: use a modified copy of request.POST
  hidden_filter_form = forms.HiddenFilterForm(choices, request.POST)

  Lock.release()

  c = RequestContext(request, {
    'lock': lock,
    'account_index': index,
    'hidden_filter_form': hidden_filter_form,
  })
  return HttpResponse(template.render(c))
