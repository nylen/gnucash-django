import os, sys

dir = os.path.dirname(__file__)
for i in range(2):
  dir = os.path.join(dir, os.path.pardir)
  if dir not in sys.path:
    sys.path.append(dir)

os.environ['DJANGO_SETTINGS_MODULE'] = 'money.settings'
os.environ['RUNNING_WSGI'] = 'true'

from django.core.handlers.wsgi import WSGIHandler
application = WSGIHandler()
