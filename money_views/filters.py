import datetime
import itertools
import operator
import re
from decimal import Decimal

from django.db.models import F, Q, Count, Sum

import settings
from gnucash_data.models import Split, Lock, Rule, RuleAccount, Transaction


class TransactionSplitFilter():
  REGEX_CHARS = '^$()[]?*+|\\'

  def __init__(self, accounts):
    self.accounts = accounts
    self.splits = reduce(operator.or_,
        (a.split_set.select_related(depth=3) for a in accounts))
    if len(self.accounts) > 1:
      Transaction.cache_from_splits(self.splits)
      exclude_split_guids = []
      account_guids = [a.guid for a in self.accounts]
      for s in self.splits:
        if any(os != s and os.account in self.accounts for os in s.transaction.splits):
          exclude_split_guids.append(s.guid)
      self.splits = self.splits.exclude(guid__in=exclude_split_guids)
    self.filtered_splits = self.splits
    self.any_filters_applied = False
    self.one_opposing_account_filter_applied = False

  def filter_splits(self, data):
    self.opposing_account_guids = data['opposing_accounts']
    if self.opposing_account_guids and 'all' not in self.opposing_account_guids:
      if any(a.guid in self.opposing_account_guids for a in self.accounts):
        raise ValueError('Tried to filter transactions on account = opposing_account')
      self.any_filters_applied = True
      if len(self.opposing_account_guids) == 1:
        self.one_opposing_account_filter_applied = True
      self.filtered_splits = \
        self.filtered_splits.filter(transaction__split__account__guid__in=self.opposing_account_guids)

    self.tx_desc = data['tx_desc']
    if self.tx_desc:
      self.any_filters_applied = True
      self.tx_desc_is_regex = TransactionSplitFilter.tx_desc_is_regex(self.tx_desc)
      if self.tx_desc_is_regex:
        self.filtered_splits = \
          self.filtered_splits.filter(transaction__description__iregex=self.tx_desc)
      else:
        self.filtered_splits = \
          self.filtered_splits.filter(transaction__description__icontains=self.tx_desc)

    self.min_date = data['min_date']
    if self.min_date:
      self.any_filters_applied = True
      self.filtered_splits = \
        self.filtered_splits.filter(transaction__post_date__gte=self.min_date)

    self.max_date = data['max_date']
    if self.max_date:
      self.any_filters_applied = True
      # Yes, this is weird.  No, it doesn't work otherwise.
      self.filtered_splits = \
        self.filtered_splits.filter(transaction__post_date__lt=self.max_date + datetime.timedelta(days=1))

    self.min_amount = data['min_amount']
    self.max_amount = data['max_amount']
    # ugh
    if self.min_amount:
      self.any_filters_applied = True
      self.min_amount -= Decimal('1e-8')
    if self.max_amount:
      self.any_filters_applied = True
      self.max_amount += Decimal('1e-8')

    if self.min_amount and self.max_amount:
      self.filtered_splits = self.filtered_splits.filter(
        (Q(value_num__gte=F('value_denom') *  self.min_amount) & Q(value_num__lte=F('value_denom') *  self.max_amount)) |
        (Q(value_num__lte=F('value_denom') * -self.min_amount) & Q(value_num__gte=F('value_denom') * -self.max_amount)))
    elif self.min_amount:
      self.filtered_splits = self.filtered_splits.filter(
        (Q(value_num__gte=F('value_denom') *  self.min_amount)) |
        (Q(value_num__lte=F('value_denom') * -self.min_amount)))
    elif self.max_amount:
      self.filtered_splits = self.filtered_splits.filter(
        (Q(value_num__lte=F('value_denom') *  self.max_amount)) |
        (Q(value_num__gte=F('value_denom') * -self.max_amount)))

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

  @staticmethod
  def tx_desc_is_regex(tx_desc):
    for c in TransactionSplitFilter.REGEX_CHARS:
      if c in tx_desc:
        return True
    return False

  def get_merchants_info(self, opposing_account):
    opposing_splits = self.splits \
      .filter(transaction__split__account=opposing_account) \
      .select_related(depth=3)
    groups = opposing_splits.values('transaction__description', 'value_denom') \
      .annotate(count=Count('guid'), value_num=Sum('value_num')) \
      .order_by('-count', 'value_denom', 'value_num', 'transaction__description')

    merchants = []
    merchant = {'description': None}

    i = 0
    any_transactions = False
    for g in groups:
      any_transactions = True
      if merchant['description'] != g['transaction__description']:
        if merchant['description'] != None:
          i += 1
          if i >= settings.NUM_MERCHANTS_BATCH_CATEGORIZE:
            break
          merchants.append(merchant)
        tx_desc = g['transaction__description']
        if TransactionSplitFilter.tx_desc_is_regex(tx_desc):
          tx_desc = re.escape(tx_desc)
        merchant = {
          'description': g['transaction__description'],
          'tx_desc': tx_desc,
          'count': 0,
          'amount': Decimal(0),
          'html_name': 'merchant_' + str(i),
          'ref_html_name': 'merchant_name_' + str(i),
          'index': i + 1,
        }
      merchant['count'] += g['count']
      merchant['amount'] += Decimal(g['value_num']) / Decimal(g['value_denom'])

    if any_transactions:
      merchants.append(merchant)

    return merchants


class RuleHelper():
  @staticmethod
  def apply(**kwargs):
    splits           = kwargs['splits']
    accounts         = splits.accounts
    tx_desc          = kwargs.get('tx_desc', None)
    is_regex         = kwargs.get('is_regex', False)
    opposing_account = kwargs['opposing_account']
    min_amount       = kwargs.get('min_amount', None)
    max_amount       = kwargs.get('max_amount', None)
    save_rule        = kwargs['save_rule']

    if min_amount is None:
      min_amount = 0
    elif min_amount < 0:
      raise ValueError('min_amount (%s) < 0' % min_amount)
    if max_amount is None:
      max_amount = 0
    elif max_amount < 0:
      raise ValueError('max_amount (%s) < 0' % max_amount)
    if min_amount and max_amount and min_amount > max_amount:
      raise ValueError('min_amount (%s) > max_amount (%s)' % (min_amount, max_amount))

    filtered_splits = splits.filtered_splits

    if tx_desc:
      # Need to do tx_desc filter ourselves
      if is_regex:
        filtered_splits = \
          filtered_splits.filter(transaction__description__iregex=tx_desc)
      else:
        filtered_splits = \
          filtered_splits.filter(transaction__description__icontains=tx_desc)
    else:
      # Any tx_desc filtering has already been done for us
      tx_desc = splits.tx_desc
      is_regex = splits.tx_desc_is_regex

    tx_guids = filtered_splits.distinct().values('transaction__guid')
    splits_real = Split.objects \
        .filter(transaction__guid__in=tx_guids) \
        .exclude(account__guid__in=[a.guid for a in accounts])

    split_guids = list(splits_real.distinct().values_list('guid', flat=True))
    tx_count = len(split_guids)
    modified_tx_count = 0

    if tx_count > 0:
      Lock.obtain()
      try:
        splits = Split.objects.filter(guid__in=split_guids)
        if opposing_account is None:
          tx_guids = list(splits.values_list('transaction__guid', flat=True))
          Transaction.objects.filter(guid__in=tx_guids).delete()
          Split.objects.filter(guid__in=split_guids).delete()
        else:
          splits.update(account=opposing_account)
        modified_tx_count = tx_count
      finally:
        Lock.release()

    if save_rule and tx_desc:
      rule = Rule()
      if opposing_account:
        rule.opposing_account_guid = opposing_account.guid
      else:
        rule.opposing_account_guid = None
      rule.match_tx_desc = tx_desc
      rule.is_regex = is_regex
      if min_amount: rule.min_amount = min_amount
      if max_amount: rule.max_amount = max_amount
      rule.save()

      for a in accounts:
        rule_account = RuleAccount()
        rule_account.rule = rule
        rule_account.account_guid = a.guid
        rule_account.save()

    return modified_tx_count
