from django.contrib.auth.decorators import login_required
from django.core.paginator          import Paginator, EmptyPage, PageNotAnInteger
from django.db                      import connections
from django.db.models               import F
from django.http                    import HttpResponse
from django.template                import RequestContext, loader

from gnucash_data.models            import Account, Split
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

  opposing_account_choices = []
  change_account_choices = []

  for row in cursor.fetchall():
    if row[3]:
      opposing_account_choices.append((row[0], row[1]))
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
        change_account_choices.append((guid, a['path']))

  get_account_path = lambda a: accounts_dict[a[0]]['path']
  opposing_account_choices.sort(key=get_account_path)
  change_account_choices.sort(key=get_account_path)

  opposing_account_choices = \
    forms.DEFAULT_OPPOSING_ACCOUNT_CHOICES + opposing_account_choices
  change_account_choices = \
    forms.DEFAULT_CHANGE_ACCOUNT_CHOICES + change_account_choices


  filter_form = forms.FilterForm(opposing_account_choices, request.GET)

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


  modify_form = forms.ModifyForm(change_account_choices, opposing_account_choices,
    request.GET, auto_id="modify_id_%s")


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
    'accounts_js': json.dumps(accounts_dict),
    'account': account,
    'page': page,
    'filter_form': filter_form,
    'modify_form': modify_form,
  })
  return HttpResponse(template.render(c))

