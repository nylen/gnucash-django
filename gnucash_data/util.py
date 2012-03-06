from dateutil import tz

def utc_to_local(utc):
  return utc.replace(tzinfo=tz.tzutc()).astimezone(tz.tzlocal())
