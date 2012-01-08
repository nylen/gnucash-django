from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

import os

urlpatterns = patterns('',
    (r'^money/$', 'money.views.index'),
    (r'^money/accounts/(?P<index>[0-9]+)$', 'money.views.account'),

    # Should be able to disable the following starting in Django 1.3
    (r'^money/static/(?P<path>.*)$', 'django.views.static.serve',
      {'document_root': os.path.join(os.path.dirname(__file__), 'money_templates/static')}),

    # Uncomment the admin/doc line below to enable admin documentation:
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
)
