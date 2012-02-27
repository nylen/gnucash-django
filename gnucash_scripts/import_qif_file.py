#!/usr/bin/env python

from common   import *
from datetime import datetime
from dateutil import parser as dateparser
from decimal  import Decimal
from gnucash  import Session, Account, Transaction, Split, GncNumeric
from sys      import argv
from time     import mktime

import os
import sys
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

# begin GnuCash API session
session = Session(settings.GNUCASH_CONN_STRING)

try:

  book = session.book
  USD = book.get_table().lookup('ISO4217', 'USD')

  root = book.get_root_account()
  acct = get_account_by_path(root, argv[1])
  imbalance = get_account_by_path(root, 'Imbalance-USD')

  # TODO: Do we need to use list() here? (time vs memory tradeoff)
  ids = set(get_transaction_id(s.parent, acct) for s in acct.GetSplitList())

  updated = False

  for fn in argv[2:]:
    balance = None
    try:
      bal = open(fn + '.balance.txt', 'r')
      for line in bal:
        line = line.rstrip()
        if line:
          balance = Decimal(line.rstrip())
    except:
      pass

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
          # Key tests: 1.1, -1.1, 9.92, -9.92
          txinfo['cents'] = int(round(float(value.replace(',', '')) * 100))

        elif marker == 'M':
          txinfo['memo'] = value

        elif marker == '^' and txinfo <> {}:
          updated = True
          # End of transaction - add it
          this_id = (txinfo['date'], txinfo['description'], txinfo['cents'])
          if this_id in ids:
            print 'Not adding duplicate transaction %s' % str(this_id)
          else:
            print 'Adding transaction %s' % str(this_id)
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
            split1.SetValue(GncNumeric(txinfo['cents'], 100))
            split1.SetAmount(GncNumeric(txinfo['cents'], 100))
            split1.SetReconcile('c')

            trans.CommitEdit()
            ids.add(this_id)
            txinfo = {}

    qif.close()

  if updated:
    u = models.Update()
    u.account = acct.GetGUID().to_string()
    u.updated = datetime.utcnow()
    u.balance = balance
    u.save(using='default')

  session.save()

finally:
  session.end()
  session.destroy()
