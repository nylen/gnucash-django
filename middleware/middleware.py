from gnucash_data.models import Account, Transaction

class ClearCachesMiddleware():
  def process_request(self, request):
    Account.clear_caches()
    Transaction.clear_caches()
    return None
