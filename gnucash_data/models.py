from django.db        import connections, models
from django.db.models import Max
from decimal          import Decimal


class Book(models.Model):
  from_gnucash_api = True

  guid = models.CharField(max_length=32, primary_key=True)
  root_account = models.ForeignKey('Account', db_column='root_account_guid')

  class Meta:
    db_table = 'books'


class Account(models.Model):
  from_gnucash_api = True

  guid = models.CharField(max_length=32, primary_key=True)
  name = models.CharField(max_length=2048)
  parent = models.ForeignKey('self', db_column='parent_guid')
  type = models.CharField(max_length=2048, db_column='account_type')

  class Meta:
    db_table = 'accounts'

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

  def __unicode__(self):
    return self.name

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

  def last_updated(self):
    cursor = connections['default'].cursor()
    cursor.execute('''
        SELECT MAX(updated)
        FROM account_updates
        WHERE account_guid = %s
      ''', [self.guid])
    u = cursor.fetchone()
    if u is None:
      return self.last_transaction_date()
    return u[0]

  def is_root(self):
    return self.guid == Account.get_root().guid

  def path(self):
    parts = []
    a = self
    while not a.is_root():
      parts.append(a.name)
      a = a.parent
    parts.reverse()
    return ':'.join(parts)


class Update(models.Model):
  account = models.CharField(max_length=32, db_column='account_guid')
  updated = models.DateTimeField()

  class Meta:
    db_table = 'account_updates'


class Transaction(models.Model):
  from_gnucash_api = True

  guid = models.CharField(max_length=32, primary_key=True)
  post_date = models.DateField()
  enter_date = models.DateTimeField()
  description = models.CharField(max_length=2048)

  class Meta:
    db_table = 'transactions'

  def __unicode__(self):
    return '%s - %s' % (str(self.post_date), self.description)


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

  def amount(self):
    return Decimal(self.value_num) / Decimal(self.value_denom)

  def is_credit(self):
    return self.amount() > 0

  def opposing_split_set(self):
    return self.transaction.split_set.exclude(account__guid=self.account.guid).all()

  def opposing_account(self):
    return self.opposing_split_set()[0].account

  def __unicode__(self):
    return '%s - %s - %0.2f' % (
        unicode(self.account),
        unicode(self.transaction),
        self.amount())

