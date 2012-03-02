from datetime import datetime
from gnucash  import Account

def get_account_by_path(acct, path):
  for name in str(path).split(':'):
    acct = acct.lookup_by_name(name)
  return acct

def get_account_by_guid(acct, guid):
  for ptr in acct.get_descendants():
    a = Account(instance=ptr)
    if a.GetGUID().to_string() == guid:
      return a
  return None

def get_account_path(acct):
  path = []
  while acct.get_full_name() <> '': # while not root account
    path.append(acct.name)
    acct = acct.get_parent()
  path.reverse()
  return ':'.join(path)

def get_transaction_id(trans, acct):
  return (datetime.fromtimestamp(trans.GetDate()).date(),
      trans.GetDescription(),
      int(round(get_transaction_amount(trans, acct)*100)))

def get_transaction_amount(trans, acct):
  amt = 0
  for s in trans.GetSplitList():
    if is_same_account(s.GetAccount(), acct):
      amt += s.GetAmount().to_double()
  return amt

def is_same_account(acct1, acct2):
  return acct1.GetGUID().to_string() == acct2.GetGUID().to_string()
