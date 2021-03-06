#!/usr/bin/env python

from sys import argv

from gnucash import Session

from common import get_account_by_path

session = Session(argv[1])
root = session.book.get_root_account()

acct = get_account_by_path(root, argv[2])

for s in acct.GetSplitList():
  desc = s.parent.GetDescription()
  memo = s.GetMemo()
  swapping = "not swapping"
  if memo <> "":
    s.parent.SetDescription(memo)
    s.SetMemo(desc)
    swapping = "swapping    "
  print '%s - desc="%s" :: memo="%s"' % (swapping, desc, memo)

session.save()
session.end()
