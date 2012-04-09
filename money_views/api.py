import json

from django.core.urlresolvers import reverse
from django.http              import HttpResponse

from gnucash_data.models import Split, Lock, Account


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
        return HttpResponseForbidden()
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
