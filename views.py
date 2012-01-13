from django.contrib.auth.decorators import login_required
from django.core.paginator          import Paginator, EmptyPage, PageNotAnInteger
from django.http                    import HttpResponse
from django.template                import RequestContext, loader

from gnucash_data.models            import Account
from utils.misc_functions           import utc_to_local

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

  splits = a.split_set.select_related(depth=1).order_by(
    'transaction__post_date',
    'transaction__enter_date',
    'guid').reverse()
  pages = Paginator(splits, 50)

  try:
    page_num = int(request.GET.get('page'))
  except:
    page_num = 1

  try:
    page = pages.page(page_num)
  except PageNotAnInteger:
    page = pages.page(1)
  except EmptyPage:
    page = pages.page(pages.num_pages)

  c = RequestContext(request, {
    'acct': acct,
    'page': page,
  })
  return HttpResponse(template.render(c))

