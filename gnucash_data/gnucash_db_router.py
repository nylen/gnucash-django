class GnucashDataRouter(object):
  def db_for_read(self, model, **hints):
    if model.from_gnucash_api:
      return 'gnucash'
    else:
      return 'default'

  def db_for_write(self, model, **hints):
    if model.from_gnucash_api:
      return 'gnucash'
    else:
      return 'default'

  def allow_syncdb(self, db, model):
    if model.from_gnucash_api:
      return (db == 'gnucash')
    else:
      return (db != 'gnucash')
