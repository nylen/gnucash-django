from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^$', 'money_views.views.index'),
    (r'^any_account$', 'money_views.views.any_account'),
    (r'^accounts/(?P<key>[0-9a-f+]+)$', 'money_views.views.account'),
    (r'^accounts/(?P<key>[0-9a-f+]+)/csv$', 'money_views.views.account_csv'),
    (r'^accounts/(?P<key>[0-9a-f+]+)/modify$', 'money_views.views.modify'),
    (r'^accounts/(?P<key>[0-9a-f+]+)/categorize$', 'money_views.views.batch_categorize'),
    (r'^accounts/(?P<key>[0-9a-f+]+)/categorize/apply$', 'money_views.views.apply_categorize'),

    (r'^accounts/(?P<key>[0-9a-f]+)/transactions/new$', 'money_views.views.new_transaction'),

    (r'^transaction/(?P<guid>[0-9a-f]+)/files$', 'money_views.views.transaction_files'),
    (r'^transaction/(?P<guid>[0-9a-f]+)/files/upload$', 'money_views.views.transaction_upload_file'),
    (r'^transaction/(?P<guid>[0-9a-f]+)/files/delete/(?P<hash>[0-9a-f]+)$', 'money_views.views.transaction_delete_file'),

    (r'^api/change_memo$', 'money_views.api.change_memo'),
    (r'^api/change_account$', 'money_views.api.change_account'),
    (r'^api/transactions$', 'money_views.api.get_transactions'),

    (r'^static/(?P<path>.*)$', 'django.contrib.staticfiles.views.serve'),

    # Uncomment the admin/doc line below to enable admin documentation:
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),

    # Login
    (r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
)
