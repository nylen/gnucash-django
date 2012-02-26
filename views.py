from django.contrib.auth.decorators import login_required
from django.core.paginator          import Paginator, EmptyPage, PageNotAnInteger
from django.db                      import connections
from django.db.models               import F
from django.http                    import HttpResponse
from django.template                import RequestContext, loader

from gnucash_data.models            import Account, Split
from utils.misc_functions           import utc_to_local

import datetime

import forms
import settings


def get_account_object(acct, index=None):
  return {
    'name': acct.name,
    'balance': acct.balance(),
    'type': acct.type.title(),
    'updated': utc_to_local(acct.last_updated()),
    'last_transaction': utc_to_local(acct.last_transaction_date()),
    'show_link': (index != None),
    'index': index,
  }


@login_required
def index(request):
  template = loader.get_template('index.html')
  accts = []
  i = 0
  for path in settings.ACCOUNTS_LIST:
    a = Account.from_path(path)
    accts.append(get_account_object(a, i))
    i += 1

  c = RequestContext(request, {
    'accounts': accts,
  })
  return HttpResponse(template.render(c))


@login_required
def account(request, index):
  template = loader.get_template('account_details.html')
  path = settings.ACCOUNTS_LIST[int(index)]
  a = Account.from_path(path)
  acct = get_account_object(a)

  items_per_page = 50

  splits = a.split_set.select_related(depth=3)

  filtering_opposing_accounts = False

  cursor = connections['gnucash'].cursor()
  cursor.execute('''
      SELECT a.guid, a.name
      FROM accounts a

      INNER JOIN (
        SELECT s2.account_guid, t.post_date
        FROM splits s
        INNER JOIN transactions t
        ON s.tx_guid = t.guid
        INNER JOIN splits s2
        on s2.tx_guid = t.guid
        WHERE s.account_guid = %s
        AND s2.account_guid <> %s
      ) s
      ON s.account_guid = a.guid

      GROUP BY 1,2
      ORDER BY MAX(s.post_date) DESC
    ''', [a.guid, a.guid])

  choices = list(forms.DEFAULT_OPPOSING_ACCOUNT_CHOICES)
  for row in cursor.fetchall():
    choices.append((row[0], row[1]))

  filter_form = forms.FilterForm(choices, request.GET)

  if filter_form.is_valid():

    opposing_account_guids = filter_form.cleaned_data['opposing_accounts']
    if opposing_account_guids and 'all' not in opposing_account_guids:
      filtering_opposing_accounts = True
      splits = splits.filter(transaction__split__account__guid__in=opposing_account_guids)

    tx_desc = filter_form.cleaned_data['tx_desc']
    if tx_desc:
      splits = splits.filter(transaction__description__icontains=tx_desc)

    min_date = filter_form.cleaned_data['min_date']
    if min_date:
      splits = splits.filter(transaction__post_date__gte=min_date)
      min_date = splits.count()

    max_date = filter_form.cleaned_data['max_date']
    if max_date:
      # Yes, this is weird.  No, it doesn't work otherwise.
      splits = splits.filter(transaction__post_date__lt=max_date + datetime.timedelta(days=1))
      max_date = splits.count()

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
    'filtering_opposing_accounts': filtering_opposing_accounts,
    'acct': acct,
    'page': page,
    'filter_form': filter_form,
  })
  return HttpResponse(template.render(c))

