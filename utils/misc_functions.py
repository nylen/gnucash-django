import calendar
from dateutil import tz

import settings

from gnucash_data.models import Account

def utc_to_local(utc):
  return utc.replace(tzinfo=tz.tzutc()).astimezone(tz.tzlocal())

def format_thousands(value, sep=','):
  s = str(value)
  if len(s) <= 3: return s
  return format_thousands(s[:-3], sep) + sep + s[-3:]

def format_decimal(value):
  value = abs(value)
  cents = ('%.2f' % (value - int(value)))[1:]
  return '%s%s' % (format_thousands(int(value)), cents)

def format_dollar_amount(value, allow_negative=False):
  if allow_negative and value < 0:
    sign = '-'
  else:
    sign = ''
  return sign + '$' + format_decimal(value)

def format_date(date):
  return date.strftime('%m/%d/%y')

def format_date_time(date):
  return date.strftime('%b %d, %Y %I:%M:%S %p')

def index1_in(value, coll):
  return coll.index(value) + 1

def get_accounts_by_webapp_key(key):
  return [get_account_by_webapp_key(k) for k in key.split('+')]

def get_account_by_webapp_key(key):
  try:
    path = settings.ACCOUNTS_LIST[int(key)]
    return Account.from_path(path)
  except ValueError:
    return Account.get(key)

def accounts_webapp_key(accounts):
  return '+'.join(a.webapp_key for a in accounts)

def date_to_timestamp(d):
  return calendar.timegm(d.timetuple()) * 1000 + d.microsecond / 1000;
