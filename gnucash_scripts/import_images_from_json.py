#!/usr/bin/env python

import json
import mimetypes
import os
import sys
from datetime import datetime
from dateutil import parser as dateparser
from decimal  import Decimal

from common import *

# Add Django project directory (parent directory of current file) to path
# This shouldn't be so hard...
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

# Django setup
# from http://www.b-list.org/weblog/2007/sep/22/standalone-django-scripts/
# This script needs to be callable from the command line, but it also needs
# to know about the Django project's database and other settings.
from django.core.management import setup_environ
import settings # only works due to path fuckery above
setup_environ(settings)

from django.core.files import uploadedfile
from gnucash_data      import models
from utils             import data_url
from utils.AsciiDammit import asciiDammit

# begin a session
models.Lock.obtain()

debug = False

def debug_print(s):
  if debug:
    print s


def get_transaction_string(t):
  memo = txinfo.get('memo', '')
  if memo:
    memo = ' / ' + memo
  return "'%s%s' on %s for %s" \
    % (t['description'], memo,
      t['date'].strftime('%Y-%m-%d'),
      t['amount'])

try:

  for fn in sys.argv[1:]:
    if fn.upper() == 'DEBUG':
      debug = True
      continue

    f = open(fn, 'r')
    data = json.load(f)
    for bank in data:
      msg = bank.get('error', bank.get('status', ''))
      if msg:
        debug_print('Skipping bank %s: %s' % (
          bank['bank'], msg))
        continue

      debug_print('Processing bank %s' % bank['bank'])

      for acct_data in bank['data']:
        msg = acct_data.get('error', acct_data.get('status', ''))
        if msg:
          debug_print('Skipping account %s: %s' % (
            acct_data['account']['path'], msg))
          continue

        debug_print('Processing account %s' % acct_data['account']['path'])

        acct = models.Account.from_path(acct_data['account']['path'])

        for txinfo in acct_data['transactions']:
          txinfo['date']        = dateparser.parse(txinfo['date']).date() # treats as MM/DD/YYYY (good)
          txinfo['amount']      = Decimal(txinfo['amount'])
          txinfo['description'] = asciiDammit(txinfo.get('description', ''))

          if txinfo.has_key('memo'):
            txinfo['memo'] = asciiDammit(txinfo['memo'])

          if not txinfo.has_key('images'):
            continue

          imported_transactions = models.ImportedTransaction.objects.filter(source_tx_id=txinfo['sourceId'])

          if imported_transactions.count() == 0:
            debug_print('Transaction has not been imported yet: %s'
              % get_transaction_string(txinfo))

          else:
            for itrans in imported_transactions:
              try:
                trans = models.Transaction.objects.get(guid=itrans.tx_guid)
              except Exception as e:
                debug_print('Error getting transaction "%s": %s'
                  % (get_transaction_string(txinfo), e))
                continue

              for (img_basename, img_data_url) in txinfo['images'].iteritems():
                img = data_url.parse(img_data_url)
                img_filename = img_basename + img.extension

                debug_print('Attaching image %s to transaction: %s'
                  % (img_filename, trans))

                img_file = uploadedfile.SimpleUploadedFile(
                  name=img_filename,
                  content=img.data,
                  content_type=img.mime_type
                )
                trans.attach_file(img_file)
                img_file.close()

    f.close()

finally:
  debug_print('Unlocking GnuCash database')
  try:
    models.Lock.release()
  except Exception as e:
    print 'Error unlocking GnuCash database: %s' % e
    pass

debug_print('Done importing images from JSON file(s)')
