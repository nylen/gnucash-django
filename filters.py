from gnucash_data.models import Account, Split

import datetime

class TransactionSplitFilter():
  REGEX_CHARS = '^$()[]?*+|\\'

  def __init__(self, account):
    self.account = account
    self.splits = account.split_set.select_related(depth=3)
    self.filtered_splits = self.splits
    self.any_filters_applied = False
    self.opposing_account_filter_applied = False

  def filter_splits(self, data):
    opposing_account_guids = data['opposing_accounts']
    if opposing_account_guids and 'all' not in opposing_account_guids:
      if self.account.guid in opposing_account_guids:
        raise ValueError('Tried to filter transactions on account = opposing_account')
      self.any_filters_applied = True
      self.opposing_account_filter_applied = True
      self.filtered_splits = \
        self.filtered_splits.filter(transaction__split__account__guid__in=opposing_account_guids)

    tx_desc = data['tx_desc']
    if tx_desc:
      self.any_filters_applied = True
      if True in (c in tx_desc for c in TransactionSplitFilter.REGEX_CHARS):
        self.filtered_splits = \
          self.filtered_splits.filter(transaction__description__iregex=tx_desc)
      else:
        self.filtered_splits = \
          self.filtered_splits.filter(transaction__description__icontains=tx_desc)

    min_date = data['min_date']
    if min_date:
      self.any_filters_applied = True
      self.filtered_splits = \
        self.filtered_splits.filter(transaction__post_date__gte=min_date)

    max_date = data['max_date']
    if max_date:
      self.any_filters_applied = True
      # Yes, this is weird.  No, it doesn't work otherwise.
      self.filtered_splits = \
        self.filtered_splits.filter(transaction__post_date__lt=max_date + datetime.timedelta(days=1))

  @staticmethod
  def _ordered_splits(splits):
    return splits.order_by(
      'transaction__post_date',
      'transaction__enter_date',
      'guid').reverse()

  def order_splits(self):
    self.splits = TransactionSplitFilter._ordered_splits(self.splits)

  def order_filtered_splits(self):
    self.filtered_splits = TransactionSplitFilter._ordered_splits(self.filtered_splits)
