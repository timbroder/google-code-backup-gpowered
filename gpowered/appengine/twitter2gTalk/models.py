from google.appengine.ext import db

class Account(db.Model):
    user = db.UserProperty(required = True)
    gLogin = db.StringProperty(required = False)
    gPass = db.StringProperty(required = True)
    twitter = db.StringProperty(required = True)
    active = db.BooleanProperty(required = True)
    counts = db.IntegerProperty(required = True)
    
class RsaKey(db.Model):
    name = db.StringProperty(required = True)
    keystring = db.StringProperty(required = True)