import os
import re
import socket
from decimal import Decimal

from django.db        import connections, models
from django.db.models import Max

import settings


class Book(models.Model):
  from_gnucash_api = True

  guid = models.CharField(max_length=32, primary_key=True)
  root_account = models.ForeignKey('Account', db_column='root_account_guid')

  class Meta:
    db_table = 'books'

  def __unicode__(self):
    return 'Root account: %s' % self.root_account


class Account(models.Model):
  from_gnucash_api = True

  guid = models.CharField(max_length=32, primary_key=True)
  name = models.CharField(max_length=2048)
  parent = models.ForeignKey('self', db_column='parent_guid', null=True)
  type = models.CharField(max_length=2048, db_column='account_type')

  class Meta:
    db_table = 'accounts'

  def __unicode__(self):
    return self.path()

  @staticmethod
  def from_path(path):
    parts = path.split(':')
    a = Account.get_root()
    if len(parts) > 0:
      for p in parts:
        a = a.account_set.get(name=p)
    return a

  @staticmethod
  def get_root():
    return Book.objects.get().root_account

  def balance(self):
    #return sum(s.amount() for s in self.split_set.all()) # SLOW
    cursor = connections['gnucash'].cursor()
    cursor.execute('''
        SELECT value_denom, SUM(value_num)
        FROM splits
        WHERE account_guid = %s
        GROUP BY 1
      ''', [self.guid])
    amount = Decimal(0)
    for row in cursor.fetchall():
      amount += row[1] / row[0]
    return amount

  def last_transaction_date(self):
    s = self.split_set.select_related(depth=1)
    utc = s.aggregate(max_date=Max('transaction__enter_date'))['max_date']
    return utc

  def has_updates(self):
    return (Update.objects.filter(account_guid=self.guid).count() > 0)

  def last_update(self):
    updates = Update.objects.filter(account_guid=self.guid)
    try:
      max_updated = updates.aggregate(max_updated=Max('updated'))['max_updated']
      return updates.filter(updated=max_updated).get()
    except:
      return None

  def is_root(self):
    return self.guid == Account.get_root().guid

  def path(self):
    if self.parent is None:
      return self.name
    parts = []
    a = self
    while not a.is_root():
      parts.append(a.name)
      a = a.parent
    parts.reverse()
    return ':'.join(parts)

  def webapp_key(self):
    try:
      return settings.ACCOUNTS_LIST.index(self.path())
    except ValueError:
      return self.guid


class Update(models.Model):
  account_guid = models.CharField(max_length=32)
  updated = models.DateTimeField()
  balance = models.DecimalField(max_digits=30, decimal_places=5, null=True)

  class Meta:
    db_table = 'account_updates'

  def __unicode__(self):
    return "Account '%s' updated at %s (balance: %s)" % (
      Account.objects.get(guid=self.account_guid),
      self.updated,
      '?' if self.balance is None else '%0.2f' % self.balance)


class ImportedTransaction(models.Model):
  account_guid = models.CharField(max_length=32)
  tx_guid = models.CharField(max_length=32)
  source_tx_id = models.CharField(max_length=2048)
  update = models.ForeignKey(Update)

  class Meta:
    db_table = 'imported_transactions'

  def __unicode__(self):
    return "Account '%s', transaction '%s', source ID '%s'" % (
      Account.objects.get(guid=self.account_guid),
      Transaction.objects.get(guid=self.tx_guid),
      self.source_tx_id);


class Transaction(models.Model):
  from_gnucash_api = True

  guid = models.CharField(max_length=32, primary_key=True)
  post_date = models.DateField()
  enter_date = models.DateTimeField()
  description = models.CharField(max_length=2048)

  class Meta:
    db_table = 'transactions'

  def __unicode__(self):
    return '%s | %s' % (self.post_date, self.description)

  def any_split_has_memo(self):
    for split in self.split_set.all():
      if not split.memo_is_id_or_blank():
        return True
    return False

  @staticmethod
  def is_id_string(s):
    return bool(re.search('id:|ref:|t(x|rans(action)?) *id', s, re.I))


class Split(models.Model):
  from_gnucash_api = True

  guid = models.CharField(max_length=32, primary_key=True)
  account = models.ForeignKey(Account, db_column='account_guid')
  transaction = models.ForeignKey(Transaction, db_column='tx_guid')
  memo = models.CharField(max_length=2048)
  value_num = models.IntegerField()
  value_denom = models.IntegerField()

  class Meta:
    db_table = 'splits'

  def __unicode__(self):
    return '%s | %s | %0.2f' % (
      self.account,
      self.transaction,
      self.amount())

  def amount(self):
    return Decimal(self.value_num) / Decimal(self.value_denom)

  def is_credit(self):
    return self.amount() > 0

  def memo_is_id_or_blank(self):
    return (not self.memo or Transaction.is_id_string(self.memo))

  def opposing_split_set(self):
    return self.transaction.split_set.exclude(account__guid=self.account.guid).all()

  def opposing_account(self):
    return self.opposing_split_set()[0].account


class Lock(models.Model):
  from_gnucash_api = True

  hostname = models.CharField(max_length=255, db_column='Hostname')
  process_id = models.IntegerField(db_column='PID', primary_key=True)

  class Meta:
    db_table = 'gnclock'

  def __unicode__(self):
    try:
      import psutil
      name = psutil.Process(int(self.process_id)).name
    except:
      name = 'unknown process'
    return '%s:%i (%s)' % (self.hostname, self.process_id, name)

  @staticmethod
  def can_obtain():
    return (Lock.objects.count() == 0)

  @staticmethod
  def check_can_obtain():
    if not Lock.can_obtain():
      lock = Lock.objects.all()[0]
      raise IOError('Cannot lock gnucash DB tables - locked by %s' % lock)

  @staticmethod
  def obtain():
    Lock.check_can_obtain()
    # TODO: How to prevent a race condition here?
    lock = Lock()
    lock.hostname = Lock._fake_hostname()
    lock.process_id = os.getpid()
    lock.save()
    return lock

  @staticmethod
  def _fake_hostname():
    try:
      import psutil
      return '%s@%s' % (psutil.Process(os.getpid()).name, socket.gethostname())
    except ImportError:
      return socket.gethostname()

  @staticmethod
  def release():
    lock = Lock.objects \
      .filter(hostname=Lock._fake_hostname()) \
      .filter(process_id=os.getpid())
    n = lock.count()
    if n != 1:
      raise IOError('Expected 1 lock; found %i' % n)
    lock.delete()


class Rule(models.Model):
  opposing_account_guid = models.CharField(max_length=32)
  match_tx_desc = models.CharField(max_length=2048)
  is_regex = models.BooleanField()
  min_amount = models.DecimalField(max_digits=30, decimal_places=5, null=True)
  max_amount = models.DecimalField(max_digits=30, decimal_places=5, null=True)

  class Meta:
    db_table = 'rules'
    ordering = ['id']

  def __unicode__(self):
    return "Match '%s'%s -> account '%s'" % (
      self.match_tx_desc,
      ' (regex)' if self.is_regex else '',
      Account.objects.get(guid=self.opposing_account_guid))

  def is_match(self, tx_desc, amount):
    if self.is_regex:
      if not re.search(self.match_tx_desc, tx_desc, re.I):
        return False
    else:
      if not self.match_tx_desc.lower() in tx_desc.lower():
        return False

    if self.min_amount and self.max_amount:
      if not (self.min_amount <= abs(amount) and abs(amount) <= self.max_amount):
        return False
    elif self.min_amount:
      if not (self.min_amount <= abs(amount)):
        return False
    elif self.max_amount:
      if not (abs(amount) <= self.max_amount):
        return False

    return True


class RuleAccount(models.Model):
  rule = models.ForeignKey('Rule')
  account_guid = models.CharField(max_length=32)

  class Meta:
    db_table = 'rule_accounts'

  def __unicode__(self):
    return "Rule '%s' for account '%s'" % (
      self.rule,
      Account.objects.get(guid=self.account_guid))
