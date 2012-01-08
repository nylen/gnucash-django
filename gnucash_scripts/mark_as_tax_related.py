#!/usr/bin/env python

from gnucash import Session, Account

TARGET_ACCOUNT_CODE = '1234'

def mark_account_with_code_as_tax_related(account, target_code):
    """Looks at account to see if it has the target_account_code, if so
    returns True.
    If not, recursively tries to do the same to all children accounts
    of account.
    Returns False when recursion fails to find it.
    """
    if account.GetCode() == target_code:
        account.SetTaxRelated(True)
        return True
    else:
        for child in account.get_children():
            child = Account(instance=child)
            if mark_account_with_code_as_tax_related(child, target_code):
                return True
        return False
            

gnucash_session = Session("file:/home/mark/python-bindings-help/test.xac")

mark_account_with_code_as_tax_related(
    gnucash_session.book.get_root_account(),
    TARGET_ACCOUNT_CODE)

gnucash_session.save()
gnucash_session.end()
