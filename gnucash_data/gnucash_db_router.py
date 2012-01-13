def db_name(model):
  if hasattr(model, 'from_gnucash_api'):
    return 'gnucash'
  else:
    return 'default'

class GnucashDataRouter(object):
  def db_for_read(self, model, **hints):
    return db_name(model)

  def db_for_write(self, model, **hints):
    return db_name(model)

  def allow_syncdb(self, db, model):
    return (db == db_name(model))
