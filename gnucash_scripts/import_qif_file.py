#!/usr/bin/env python

import re
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

# make sure we can begin a session
models.Lock.check_can_obtain()

# begin GnuCash API session
session = Session(settings.GNUCASH_CONN_STRING)


debug = False

def debug_print(s):
  if debug:
    print s


def get_id_string(s):
  if re.search('id:|ref:|t(x|rans(action)?) *id', s, re.I):
    return s
  else:
    return None

def make_transaction_id(t):
  memo = txinfo.get('memo', '')
  id = get_id_string(memo)
  if id:
    return id
  id = get_id_string(t['description'])
  if id:
    return id
  return '%s|%s|%s|%s' % (
    t['date'].strftime('%Y-%m-%d'),
    t['description'],
    memo,
    t['amount'])

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
  acct = get_account_by_path(root, sys.argv[1])
  acct_guid = acct.GetGUID().to_string()
  imbalance = get_account_by_path(root, 'Imbalance-USD')

  rules = [ra.rule for ra in models.RuleAccount.objects
    .filter(account_guid=acct_guid).select_related().distinct('rule__id')]

  updated = False

  for fn in sys.argv[2:]:
    if fn.upper() == 'DEBUG':
      debug = True
      continue

    balance = None
    try:
      bal = open(fn + '.balance.txt', 'r')
      for line in bal:
        line = line.rstrip()
        if line:
          balance = Decimal(line)
    except:
      pass

    imported_transactions = []

    qif = open(fn, 'r')
    txinfo = {}
    for line in qif:
      line = line.rstrip() # remove newline and any other trailing whitespace
      if line <> '':
        marker = line[0]
        value = line[1:]

        if marker == 'D':
          txinfo['date'] = dateparser.parse(value).date() # treats as MM/DD/YYYY (good)

        elif marker == 'P':
          txinfo['description'] = value

        elif marker == 'T':
          txinfo['amount'] = Decimal(value.replace(',', ''))

        elif marker == 'M':
          txinfo['memo'] = value

        elif marker == '^' and txinfo <> {}:
          updated = True

          # End of transaction - add it if it's not a duplicate
          this_id = make_transaction_id(txinfo)

          if models.ImportedTransaction.objects.filter(source_tx_id=this_id).count():
            debug_print('Not adding duplicate transaction %s'
              % get_transaction_string(txinfo))
          else:
            debug_print('Adding transaction %s' % get_transaction_string(txinfo))
            gnc_amount = decimal_to_gnc_numeric(txinfo['amount'])

            # From example script 'test_imbalance_transaction.py'
            trans = Transaction(book)
            trans.BeginEdit()
            trans.SetCurrency(USD)
            trans.SetDescription(txinfo['description'])
            trans.SetDate(
              txinfo['date'].day,
              txinfo['date'].month,
              txinfo['date'].year)

            split1 = Split(book)
            split1.SetParent(trans)
            split1.SetAccount(acct)
            if txinfo.has_key('memo'):
              split1.SetMemo(txinfo['memo'])
            # The docs say both of these are needed:
            # http://svn.gnucash.org/docs/HEAD/group__Transaction.html
            split1.SetValue(gnc_amount)
            split1.SetAmount(gnc_amount)
            split1.SetReconcile('c')

            opposing_acct = None
            opposing_acct_path = None

            for rule in rules:
              if rule.is_match(txinfo['description'], txinfo['amount']):
                opposing_acct = get_account_by_guid(root, rule.opposing_account_guid)
                opposing_acct_path = get_account_path(opposing_acct)
                debug_print('Transaction %s matches rule %i (%s)'
                  % (get_transaction_string(txinfo), rule.id, opposing_acct_path))

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
            txinfo = {}

            tx = models.ImportedTransaction()
            tx.account_guid = acct_guid
            tx.tx_guid = trans.GetGUID().to_string()
            tx.source_tx_id = this_id
            imported_transactions.append(tx)

    qif.close()

  if updated:
    u = models.Update()
    u.account_guid = acct_guid
    u.updated = datetime.utcnow()
    u.balance = balance
    u.save()

    for tx in imported_transactions:
      tx.update = u
      tx.save()

  session.save()

finally:
  session.end()
  session.destroy()
