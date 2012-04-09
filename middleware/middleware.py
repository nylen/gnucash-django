from gnucash_data.models import Account

class ClearCachesMiddleware():
  def process_request(self, request):
    Account.clear_caches()
    return None
