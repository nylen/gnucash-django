#!/usr/bin/env python

import json
import os
import sys
from datetime import datetime
from dateutil import parser as dateparser
from decimal  import Decimal

from gnucash import Session, Transaction, Split, GncNumeric

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

from gnucash_data import models
from utils.AsciiDammit import asciiDammit

# make sure we can begin a session
models.Lock.check_can_obtain()

# begin GnuCash API session
session = Session(settings.GNUCASH_CONN_STRING)


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

  book = session.book
  USD = book.get_table().lookup('ISO4217', 'USD')

  root = book.get_root_account()
  imbalance = get_account_by_path(root, 'Imbalance-USD')

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

        acct = get_account_by_path(root, acct_data['account']['path'])
        acct_guid = acct.GetGUID().to_string()

        rules = [ra.rule for ra in models.RuleAccount.objects
          .filter(account_guid=acct_guid).select_related().distinct('rule__id')]

        updated = False
        imported_transactions = []

        balance = acct_data['balances'].get('actual', None)
        if balance:
          balance = Decimal(balance)

        for txinfo in acct_data['transactions']:
          updated = True
          txinfo['date'] = dateparser.parse(txinfo['date']).date() # treats as MM/DD/YYYY (good)
          txinfo['amount'] = Decimal(txinfo['amount'])
          if not txinfo.has_key('description'):
            txinfo['description'] = ''

          if models.ImportedTransaction.objects.filter(source_tx_id=txinfo['sourceId']).count():
            debug_print('Not adding duplicate transaction %s'
              % get_transaction_string(txinfo))
          else:
            opposing_acct = None
            opposing_acct_path = None

            ignore_this_transaction = False
            tx_guid = None

            for rule in rules:
              if rule.is_match(txinfo['description'], txinfo['amount']):
                if rule.opposing_account_guid is None:
                  ignore_this_transaction = True
                else:
                  opposing_acct = get_account_by_guid(root, rule.opposing_account_guid)
                  opposing_acct_path = get_account_path(opposing_acct)

                debug_print('Transaction %s matches rule %i (%s)'
                  % (get_transaction_string(txinfo), rule.id, opposing_acct_path))

            if ignore_this_transaction:

              debug_print('Ignoring transaction %s' % get_transaction_string(txinfo))

            else:

              debug_print('Adding transaction %s' % get_transaction_string(txinfo))
              gnc_amount = decimal_to_gnc_numeric(txinfo['amount'])

              # From example script 'test_imbalance_transaction.py'
              trans = Transaction(book)
              trans.BeginEdit()
              trans.SetCurrency(USD)
              trans.SetDescription(str(asciiDammit(txinfo['description'])))
              trans.SetDate(
                txinfo['date'].day,
                txinfo['date'].month,
                txinfo['date'].year)

              split1 = Split(book)
              split1.SetParent(trans)
              split1.SetAccount(acct)
              if txinfo.has_key('memo'):
                split1.SetMemo(str(asciiDammit(txinfo['memo'])))
              # The docs say both of these are needed:
              # http://svn.gnucash.org/docs/HEAD/group__Transaction.html
              split1.SetValue(gnc_amount)
              split1.SetAmount(gnc_amount)
              split1.SetReconcile('c')

              if opposing_acct != None:
                debug_print('Categorizing transaction %s as %s'
                  % (get_transaction_string(txinfo), opposing_acct_path))
                split2 = Split(book)
                split2.SetParent(trans)
                split2.SetAccount(opposing_acct)
                split2.SetValue(gnc_amount.neg())
                split2.SetAmount(gnc_amount.neg())
                split2.SetReconcile('c')

              trans.CommitEdit()
              tx_guid = trans.GetGUID().to_string()

            tx = models.ImportedTransaction()
            tx.account_guid = acct_guid
            tx.tx_guid = tx_guid
            tx.source_tx_id = txinfo['sourceId']
            imported_transactions.append(tx)

        if updated:
          u = models.Update()
          u.account_guid = acct_guid
          u.updated = datetime.utcnow()
          u.balance = balance
          u.save()

          for tx in imported_transactions:
            tx.update = u
            tx.save()

    f.close()

finally:
  debug_print('Ending GnuCash session')
  session.end()
  debug_print('Destroying GnuCash session')
  session.destroy()
  debug_print('Destroyed GnuCash session')

debug_print('Done importing JSON file(s)')
