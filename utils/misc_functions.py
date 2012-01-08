from datetime import datetime
from dateutil import tz

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

def format_dollar_amount(value):
  return '$' + format_decimal(value)

def format_date(date):
  return date.strftime('%m/%d/%y')

def format_date_time(date):
  return date.strftime('%b %d, %Y %I:%M:%S %p')
