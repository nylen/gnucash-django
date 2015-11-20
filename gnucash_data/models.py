import errno
import hashlib
import io
import os
import psutil
import re
import shutil
import socket

from decimal import Decimal
from PIL     import Image

from django.core.files import uploadedfile
from django.db         import connections, models
from django.db.models  import Max

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
  parent_guid = models.CharField(max_length=32, null=True)
  type = models.CharField(max_length=2048, db_column='account_type')
  description = models.CharField(max_length=2048)
  placeholder = models.BooleanField()

  _balances = {}
  _root = None
  _all_accounts = None
  _order = None

  class Meta:
    db_table = 'accounts'

  def __unicode__(self):
    return self.path

  @staticmethod
  def from_path(path):
    parts = path.split(':')
    a = Account.get_root()
    if len(parts) > 0:
      for p in parts:
        found = False
        for c in a.children:
          if c.name == p:
            found = True
            a = c
            break
        if not found:
          raise ValueError("Invalid account path '%s'" % path)
    return a

  @staticmethod
  def get_root():
    Account._ensure_cached()
    return Account._root

  @staticmethod
  def get(guid):
    Account._ensure_cached()
    return Account._all_accounts[guid]['account']

  @staticmethod
  def get_all():
    Account._ensure_cached()
    return [obj['account'] \
      for obj in Account._all_accounts.itervalues()]

  @staticmethod
  def _ensure_cached():
    if Account._root is None:
      Account._root = Book.objects.get().root_account

    if Account._all_accounts is None:
      def _path(account):
        if account.parent_guid is None:
          return account.name
        parts = []
        a = account
        while not a.is_root:
          parts.append(a.name)
          a = Account.get(a.parent_guid)
        parts.reverse()
        return ':'.join(parts)

      Account._all_accounts = {}
      accounts = list(Account.objects.all())

      for a in accounts:
        Account._all_accounts[a.guid] = {
          'account': a,
          'path': '',
          'children': [],
        }
      for a in accounts:
        Account._all_accounts[a.guid]['path'] = _path(a)
        if a.parent_guid is not None:
          Account._all_accounts[a.parent_guid]['children'].append(a)
      for a in accounts:
        Account._all_accounts[a.guid]['children'] \
          .sort(key=lambda a: a.name.lower())

    if Account._order is None:
      def _build_order(account):
        Account._order.append(account.guid)
        for a in account.children:
          _build_order(a)
      Account._order = []
      _build_order(Account.get_root())

  @staticmethod
  def clear_caches():
    Account._balances = {}
    Account._root = None
    Account._all_accounts = None
    Account._order = None

  @property
  def description_or_name(self):
    if self.description:
      return self.description
    else:
      return self.name

  @property
  def balance(self):
    if self.guid not in Account._balances:
      #return sum(s.amount() for s in self.split_set.all()) # SLOW
      cursor = connections['gnucash'].cursor()
      cursor.execute('''
          SELECT value_denom, SUM(value_num)
          FROM splits
          WHERE account_guid = %s
          GROUP BY value_denom
        ''', [self.guid])
      amount = Decimal(0)
      for row in cursor.fetchall():
        amount += row[1] / row[0]
      Account._balances[self.guid] = amount
    return Account._balances[self.guid]

  @property
  def last_transaction_date(self):
    s = self.split_set.select_related(depth=1)
    utc = s.aggregate(max_date=Max('transaction__enter_date'))['max_date']
    return utc

  @property
  def has_updates(self):
    return (Update.objects.filter(account_guid=self.guid).count() > 0)

  @property
  def last_update(self):
    updates = Update.objects.filter(account_guid=self.guid)
    try:
      max_updated = updates.aggregate(max_updated=Max('updated'))['max_updated']
      return updates.filter(updated=max_updated).get()
    except:
      return None

  @property
  def children(self):
    Account._ensure_cached()
    return list(Account._all_accounts[self.guid]['children'])

  @property
  def is_root(self):
    return self.guid == Account.get_root().guid

  @property
  def path(self):
    Account._ensure_cached()
    return Account._all_accounts[self.guid]['path']

  @property
  def webapp_key(self):
    try:
      return unicode(settings.ACCOUNTS_LIST.index(self.path))
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
      Account.get(self.account_guid),
      self.updated,
      '?' if self.balance is None else '%0.2f' % self.balance)


class ImportedTransaction(models.Model):
  account_guid = models.CharField(max_length=32)
  tx_guid = models.CharField(max_length=32, null=True)
  source_tx_id = models.CharField(max_length=2048)
  update = models.ForeignKey(Update)

  class Meta:
    db_table = 'imported_transactions'

  def __unicode__(self):
    return "Account '%s', transaction '%s', source ID '%s'" % (
      Account.get(self.account_guid),
      Transaction.objects.get(guid=self.tx_guid),
      self.source_tx_id);


class Transaction(models.Model):
  from_gnucash_api = True

  guid = models.CharField(max_length=32, primary_key=True)
  post_date = models.DateField()
  enter_date = models.DateTimeField()
  description = models.CharField(max_length=2048)

  _cached_transactions = {}

  class Meta:
    db_table = 'transactions'

  def __unicode__(self):
    return '%s | %s' % (self.post_date, self.description)

  def attach_file(self, f):
    return File._new_with_transaction(f, self)

  @property
  def any_split_has_memo(self):
    for split in self.splits:
      if not split.memo_is_id_or_blank:
        return True
    return False

  @staticmethod
  def is_id_string(s):
    return bool(re.search('id:|ref:|t(x|rans(action)?) *id', s, re.I))

  @property
  def splits(self):
    if self.guid in Transaction._cached_transactions:
      return Transaction._cached_transactions[self.guid]['splits']
    else:
      return self.split_set.all()

  @staticmethod
  def cache_from_splits(splits):
    transactions = Transaction.objects \
      .filter(guid__in=(s.transaction.guid for s in splits))
    splits = Split.objects \
      .select_related(depth=2) \
      .filter(transaction__guid__in=(t.guid for t in transactions))
    for tx in transactions:
      Transaction._cached_transactions[tx.guid] = {
        'transaction': tx,
        'splits': [],
      }
    for s in splits:
      Transaction._cached_transactions[s.transaction.guid]['splits'].append(s)

  @staticmethod
  def clear_caches():
    Transaction._cached_transactions = {}


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

  @property
  def amount(self):
    return Decimal(self.value_num) / Decimal(self.value_denom)

  @property
  def is_credit(self):
    return self.amount > 0

  @property
  def memo_is_id_or_blank(self):
    return (not self.memo or Transaction.is_id_string(self.memo))

  @property
  def opposing_split_set(self):
    return [s for s in self.transaction.splits if s.account != self.account]

  @property
  def opposing_split(self):
    try:
      return self.opposing_split_set[0]
    except:
      return None

  @property
  def opposing_account(self):
    return self.opposing_split.account


class Lock(models.Model):
  from_gnucash_api = True

  hostname = models.CharField(max_length=255, db_column='Hostname')
  process_id = models.IntegerField(db_column='PID', primary_key=True)

  class Meta:
    db_table = 'gnclock'

  def __unicode__(self):
    try:
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


class File(models.Model):
  hash = models.CharField(max_length=64)
  filename = models.CharField(max_length=255)
  transaction = models.ForeignKey(Transaction, db_column='tx_guid')

  _path = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    'static',
    'upload'
  ))

  class Meta:
    db_table = 'files'
    ordering = ['transaction', 'filename']

  def delete(self, *args, **kwargs):
    if File.objects.filter(hash=self.hash).count() == 1:
      # This is the only place this file is used; we can delete it
      # TODO: This logic does not seem to be working
      shutil.rmtree(os.path.dirname(self.abs_path))
    super(File, self).delete(*args, **kwargs)

  @property
  def extension(self):
    return '.' + self.filename.split('.')[-1].lower()

  @property
  def web_path(self):
    return 'upload/%s/%s' % (self.hash, self.filename)

  @property
  def abs_path(self):
    return os.path.join(File._path, self.hash, self.filename)

  @staticmethod
  def _new_with_transaction(f, transaction):
    # f is a Django UploadedFile

    image_type = 'image/'
    if f.content_type[:len(image_type)] == image_type:
      try:
        img = Image.open(f)
        w, h = img.size
        max_size = 1600
        if max(w, h) > max_size:
          img.thumbnail((max_size, max_size))
          tmp = io.BytesIO()
          img.save(tmp, img.format)
          tmp.seek(0)
          f = uploadedfile.SimpleUploadedFile(
            name=f.name,
            content=tmp.read(),
            content_type=f.content_type
          )
          tmp.close()
      except:
        pass
      finally:
        if img:
          img.close()

    hasher = hashlib.sha256()
    for chunk in f.chunks():
      hasher.update(chunk)
    h = hasher.hexdigest()

    test1 = File.objects.filter(hash=h)
    test2 = test1.filter(transaction=transaction)

    if test2.count() > 0:
      # This transaction already has the given file attached.
      return test2.get()

    if test1.count() > 0:
      # Another transaction already has the given file attached.
      other_file = test1[0]
      this_file = File(
        hash=other_file.hash,
        filename=other_file.filename,
        transaction=transaction
      )
      this_file.save()
      return this_file

    # Save this file to the filesystem and the database.

    this_file = File(
      hash=h,
      filename=f.name,
      transaction=transaction
    )

    try:
      os.makedirs(os.path.dirname(this_file.abs_path))
    except OSError as e:
      if e.errno != errno.EEXIST:
        raise

    with open(this_file.abs_path, 'wb') as w:
      for chunk in f.chunks():
        w.write(chunk)

    this_file.save()
    return this_file


class Rule(models.Model):
  opposing_account_guid = models.CharField(max_length=32, null=True)
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
      Account.get(self.opposing_account_guid))

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
      Account.get(self.account_guid))
