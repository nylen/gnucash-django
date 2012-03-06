from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^$', 'money_views.views.index'),
    (r'^accounts/(?P<index>[0-9]+)$', 'money_views.views.account'),
    (r'^accounts/(?P<index>[0-9]+)/modify$', 'money_views.views.modify'),
    (r'^accounts/(?P<index>[0-9]+)/categorize$', 'money_views.views.batch_categorize'),
    (r'^accounts/(?P<index>[0-9]+)/categorize/apply$', 'money_views.views.apply_categorize'),

    (r'^static/(?P<path>.*)$', 'django.contrib.staticfiles.views.serve'),

    # Uncomment the admin/doc line below to enable admin documentation:
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),

    # Login
    (r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
)
