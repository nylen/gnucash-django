import os, sys

dir = os.path.dirname(__file__)
project = os.path.basename(os.path.dirname(dir))
for i in range(2):
  dir = os.path.join(dir, os.path.pardir)
  if dir not in sys.path:
    sys.path.append(dir)

os.environ['DJANGO_SETTINGS_MODULE'] = '%s.settings' % project
os.environ['RUNNING_WSGI'] = 'true'

from django.core.handlers.wsgi import WSGIHandler
app_real = WSGIHandler()

def application(environ, start_response):
  os.environ['WSGI_SCRIPT_NAME'] = environ['SCRIPT_NAME']
  return app_real(environ, start_response)
