# vim: ft=python

import os, sys

dir = os.path.join(os.path.dirname(__file__), os.path.pardir)
if dir not in sys.path:
  sys.path.append(dir)

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
os.environ['RUNNING_WSGI'] = 'true'

from django.core.handlers.wsgi import WSGIHandler
app_real = WSGIHandler()

def application(environ, start_response):
  os.environ['WSGI_SCRIPT_NAME'] = environ['SCRIPT_NAME']
  return app_real(environ, start_response)
