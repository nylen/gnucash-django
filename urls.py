from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

import os

urlpatterns = patterns('',
    (r'^$', 'money.views.index'),
    (r'^accounts/(?P<index>[0-9]+)$', 'money.views.account'),
    (r'^accounts/(?P<index>[0-9]+)/modify$', 'money.views.modify'),
    (r'^accounts/(?P<index>[0-9]+)/categorize$', 'money.views.batch_categorize'),
    (r'^accounts/(?P<index>[0-9]+)/categorize/apply$', 'money.views.apply_categorize'),

    (r'^static/(?P<path>.*)$', 'django.contrib.staticfiles.views.serve'),

    # Uncomment the admin/doc line below to enable admin documentation:
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),

    # Login
    (r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
)
