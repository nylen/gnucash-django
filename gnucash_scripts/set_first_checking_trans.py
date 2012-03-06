#!/usr/bin/env python

from sys import argv

from gnucash import Session

from common import *

session = Session(argv[1])

try:

  root = session.book.get_root_account()
  checking = get_account_by_path(root, 'Assets:Current Assets:Trust FCU Checking')
  s = checking.GetSplitList()[0]
  t = s.parent

  s = t.GetSplitList()[0]
  print '%s :: %s' % (t.GetDescription(),
    ' // '.join(get_account_path(s.GetAccount()) for s in t.GetSplitList()))
  if len(argv) > 2:
    s.SetAccount(get_account_by_path(root, argv[2]))
    session.save()

finally:
  session.end()
  session.destroy()
