# vim: ft=python

import os
import sys

import site

path = os.path

# Remember original sys.path

prev_sys_path = list(sys.path)

# Add new directories

dir = path.realpath(path.join(path.dirname(__file__), path.pardir))
if dir not in sys.path:
  sys.path.append(dir)

site.addsitedir(path.realpath(path.join(dir, 'lib/python2.7/site-packages')))

# Reorder sys.path so that new directories are at the front
# This logic from: http://code.google.com/p/modwsgi/wiki/VirtualEnvironments

new_sys_path = []
for item in list(sys.path):
  if item not in prev_sys_path:
    new_sys_path.append(item)
    sys.path.remove(item)

sys.path[:0] = new_sys_path


os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
os.environ['RUNNING_WSGI'] = 'true'

from django.core.handlers.wsgi import WSGIHandler
app_real = WSGIHandler()

def application(environ, start_response):
  os.environ['WSGI_SCRIPT_NAME'] = environ['SCRIPT_NAME']
  return app_real(environ, start_response)
