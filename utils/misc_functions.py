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




# from https://code.djangoproject.com/wiki/ProfilingDjango
import hotshot
import os
import time
import settings

try:
  PROFILE_LOG_BASE = settings.PROFILE_LOG_BASE
except:
  PROFILE_LOG_BASE = "/tmp"


def profile(log_file):
  """Profile some callable.

  This decorator uses the hotshot profiler to profile some callable (like
  a view function or method) and dumps the profile data somewhere sensible
  for later processing and examination.

  It takes one argument, the profile log name. If it's a relative path, it
  places it under the PROFILE_LOG_BASE. It also inserts a time stamp into the
  file name, such that 'my_view.prof' become 'my_view-20100211T170321.prof',
  where the time stamp is in UTC. This makes it easy to run and compare
  multiple trials.
  """

  if not os.path.isabs(log_file):
    log_file = os.path.join(PROFILE_LOG_BASE, log_file)

  def _outer(f):
    def _inner(*args, **kwargs):
      # Add a timestamp to the profile output when the callable
      # is actually called.
      (base, ext) = os.path.splitext(log_file)
      base = base + "-" + time.strftime("%Y%m%dT%H%M%S", time.gmtime())
      final_log_file = base + ext

      prof = hotshot.Profile(final_log_file)
      try:
        ret = prof.runcall(f, *args, **kwargs)
      finally:
        prof.close()
      return ret

    return _inner
  return _outer
