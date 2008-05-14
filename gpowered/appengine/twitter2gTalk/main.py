import os, sys, re

import wsgiref.handlers
from models import Account, RsaKey

from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch
import simplejson
import rsa

_DEBUG = True

class BaseRequestHandler(webapp.RequestHandler):
  
  def generate(self, template_name, template_values={}):
    user = users.get_current_user()
    
    if user:
      log_in_out_url = users.create_logout_url('/')
    else:
      log_in_out_url = users.create_login_url(self.request.path)
    
    values = {'user': user, 'log_in_out_url': log_in_out_url}
    values.update(template_values)
    directory = os.path.dirname(__file__)
    path = os.path.join(directory, 'templates', template_name)
    self.response.out.write(template.render(path, values, debug=_DEBUG))
    
class MainHandler(BaseRequestHandler):

  def get(self):
    self.generate('base.html')
    
class SettingsHander(BaseRequestHandler):

    def get(self):
        current_user = users.get_current_user()        
        if not current_user:
            self.redirect(users.create_login_url(self.request.path))
        twitter = None
        user = Account.gql('WHERE user = :1', current_user).get()
        
        if user:
            twitter = user.twitter        
        
        self.generate('settings.html', template_values={'user': current_user,
                                                        'twitter': twitter
                                                })
    def post(self):
        current_user = users.get_current_user()        
        if not current_user:
            self.redirect(users.create_login_url(self.request.path))
        
        password = self.request.get('password')
        twitter = self.request.get('twitter')
        active = self.request.get('active')
        
        errors = []
        
        if not password:
            errors.append('Password must be filled in')
        if not twitter:
            errors.append('Twitter Account must be filled in')
        
        if len(errors) == 0:
            user = Account.gql('WHERE user = :1', current_user).get()
            if not user:
                user = Account(user=current_user, gPass=password, twitter=twitter, active=True)
            else:
                user.gPass = password
                user.twitter = twitter
                user.active = True
                
            user.put()
            errors = None
        
        self.generate('settings.html', template_values={'user': current_user,
                                                        'errors': errors
                                                })
class TweetHander(BaseRequestHandler):
        
    def makePubKey(self, k):
        temp = k.split('!')
        pubkey = {'e': long(temp[0]), 'n': long(temp[1])}
        return pubkey
    
    def makePrivKey(self, k):
        temp = k.split('!')
        privkey = {'d': long(temp[0]), 'p': long(temp[1]), 'q': long(temp[2])}        
        return privkey        
    
    def getTwitterStatus(self, username):
        twitter_url = 'http://twitter.com/statuses/user_timeline/%s.json?count=1'
        url = twitter_url % username
        result = urlfetch.fetch(url)
        
        json = simplejson.loads(str(result.content))
        
        return json[0].get('text')  
    
    def encryptGtalk(self, email, password, msg):   
        gp_pub = RsaKey.gql("WHERE name = :1", 'gp_pub').get()
        gae_priv = RsaKey.gql("WHERE name = :1", 'gae_priv').get()
           
        gpowered_gtalk_url = 'http://localhost:8000/gtalk/update/%s/'
        
        enc = '%s!gpowered!%s!gpowered!%s' % (email, password, msg)
        gp_pubkey = self.makePubKey(gp_pub.keystring)
        gae_privkey = self.makePrivKey(gae_priv.keystring)        
        
        
        
        gae_one = rsa.encrypt(str(enc), gp_pubkey)
        gae_two = rsa.sign(gae_one, gae_privkey)
        
        encrypted_url = gpowered_gtalk_url % gae_two.replace('/', '!GP!')
        
        return encrypted_url
    
    def get(self):        
        current_user = users.get_current_user()
        
        if not current_user:
            self.redirect(users.create_login_url(self.request.path))
            
        user = Account.gql('WHERE user = :1 ', current_user).get()
        
        twitter_status = None        
        twitter_status = self.getTwitterStatus(user.twitter) 
        
        gpowered_url = self.encryptGtalk(current_user.email(), user.gPass, twitter_status)
        #result = urlfetch.fetch(str(gpowered_url))     

        self.generate('update.html', template_values={
                                                   'name': current_user,  
                                                   'status': twitter_status,
                                                   'twitter': user.twitter,
                                                   'url': gpowered_url,
                                                })

def main():
  application = webapp.WSGIApplication([('/', MainHandler),
                                       ('/settings/', SettingsHander),
                                       ('/save/', SettingsHander),
                                       ('/update/', TweetHander),
                                       ],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)



if __name__ == '__main__':
  main()