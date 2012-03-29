from datetime import datetime
from decimal  import Decimal

from gnucash import Account, GncNumeric

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

def gnc_numeric_to_decimal(n):
  return Decimal(n.denom()) / Decimal(n.num())

def decimal_to_gnc_numeric(d):
  denom = 100
  d = d * denom
  while d % 1:
    denom *= 10
    d *= 10
  return GncNumeric(int(d), denom)

def is_same_account(acct1, acct2):
  return acct1.GetGUID().to_string() == acct2.GetGUID().to_string()
