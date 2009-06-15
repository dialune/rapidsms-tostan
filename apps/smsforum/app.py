#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

import re, os
import rapidsms
from rapidsms.parsers import Matcher
from rapidsms.message import Message
from models import *
from apps.locations.models import *
import gettext
import traceback

from apps.smsforum.models import *
from apps.contacts.models import *

DEFAULT_VILLAGE="unassociated"
DEFAULT_LANGUAGE="fre"

class App(rapidsms.app.App):
    SUPPORTED_LANGUAGES = ['eng','fre','pul','dyu','deb']
    
    # TODO: move to db
    MULTILINGUAL_MAP = [ # should be ordered: hence the tuples
        (SUPPORTED_LANGUAGES[0], [ #english
            ("join",  ["\s*[#\*\.]join (whatever)\s*"]), # optionally: join village name m/f age
            ("register_name",  ["\s*[#\*\.]name (whatever)\s*"]), # optionally: join village name m/f age
            ("leave",  ["\s*[#\*\.]leave.*"]),
            ("lang",  ["\s*[#\*\.]lang (slug)", "[#\*\.]?language (slug)\s*"]),
            ("help",  ["[ ]*[#\*\.]help.*"]),
            ("createvillage",  ["\s*###create (whatever)\s*"]),
        ]),
        (SUPPORTED_LANGUAGES[1], [ #french
            ("join",  ["\s*fr[#\*\.]join (whatever)\s*"]), # optionally: join village name m/f age
            ("register_name",  ["\s*fr[#\*\.]name (whatever)\s*"]), # optionally: join village name m/f age
            ("leave",  ["\s*fr[#\*\.]leave.*"]),
        ]),
        (SUPPORTED_LANGUAGES[2], [ #pular
            ("join",  ["\s*pu[#\*\.]join (whatever)\s*"]), # optionally: join village name m/f age
            ("register_name",  ["\s*pu[#\*\.]name (whatever)\s*"]), # optionally: join village name m/f age
            ("leave",  ["\s*pu[#\*\.]leave.*"]),
        ]),
        (SUPPORTED_LANGUAGES[3], [ #dyula
            ("join",  ["\s*dy[#\*\.]join (whatever)\s*"]), # optionally: join village name m/f age
            ("register_name",  ["\s*dy[#\*\.]name (whatever)\s*"]), # optionally: join village name m/f age
            ("leave",  ["\s*dy[#\*\.]leave.*"]),
        ]),
        (SUPPORTED_LANGUAGES[4], [ #english
            ("join",  ["\s*[#\*\.]djoin (whatever)\s*"]), # optionally: join village name m/f age
            ("register_name",  ["\s*[#\*\.]rname (whatever)\s*"]), # optionally: join village name m/f age
            ("leave",  ["\s*[#\*\.]dleave.*"]),
            ("lang",  ["\s*[#\*\.]dlang (slug)"]),
            ("createvillage",  ["\s*###dcreate (whatever)\s*"])
        ])
     ]
    
    def help(self, msg):
        msg.respond("Available Commands: #join VILLAGE - #name YOURNAME - #leave - #lang ENG")

    def __init__(self, router):
        rapidsms.app.App.__init__(self, router)
    
    def start(self):
        # since the functionality of this app depends on a default group
        # make sure that this group is created explicitly in this app 
        # (instead of depending on a fixture)
        self.__loadFixtures()
        self.__initTranslators()
        
        # fetch a list of all the backends
        # that we already have objects for
        known_backends = CommunicationChannel.objects.values_list("slug", flat=True)
        
        # find any running backends which currently
        # don't have objects, and fill in the gaps
        for be in self.router.backends:
            if not be.slug in known_backends:
                self.info("Creating PersistantBackend object for %s (%s)" % (be.slug, be.title))
                CommunicationChannel(slug=be.slug, title=be.title).save()    
    
    def parse(self, msg):
        print "REPORTER:PARSE"
        # fetch the persistantconnection object
        # for this message's sender (or create
        # one if this is the first time we've
        # seen the sender), and stuff the meta-
        # dta into the message for other apps
        msg.persistent_channel= CommunicationChannelFromMessage(msg)
        msg.persistant_connection = ChannelConnectionFromMessage(msg)
        msg.sender = ContactFromMessage(msg)
        
        # store a handy dictionary, containing the most useful persistance
        # information that we have. this is useful when creating an object
        # linked to _something_, like so:
        # 
        #   class SomeObject(models.Model):
        #     reporter   = models.ForeignKey(Reporter, null=True)
        #     connection = models.ForeignKey(PersistantConnection, null=True)
        #     stuff      = models.CharField()
        #
        #   # this object will be linked to a reporter,
        #   # if one exists - otherwise, a connection
        #   SomeObject(stuff="hello", **msg.persistance_dict)
        if msg.sender: msg.persistance_dict = { "reporter": msg.sender }
        else:            msg.persistance_dict = { "connection": msg.persistant_connection }
        
        # log, whether we know who the sender is or not
        if msg.sender: self.info("Identified: %s as %r" % (msg.persistant_connection.user_identifier, msg.sender))
        else:            self.info("Unidentified: %s" % (msg.persistant_connection.user_identifier))
    
    def handle(self, msg):
        print "REPORTER:HANDLE"
        matcher = Matcher(msg)
        
        # TODO: this is sort of a lightweight implementation
        # of the keyworder. it wasn't supposed to be. maybe
        # replace it *with* the keyworder, or extract it
        # into a parser of its own
        
        # search the map for a match, dispatch
        # the message to it, and return/stop
        for lang, map in self.MULTILINGUAL_MAP:
            for method, patterns in map: # search through language in default preference order
                if matcher(*patterns) and hasattr(self, method):
                    msg.sender.set_locale(lang)
                    msg.sender.save()
                    self.__setLocale(lang)
                    getattr(self, method)(msg, *matcher.groups)
                    return True
        method = "blast"
        patterns = ["(whatever)"]
        if matcher(*patterns) and hasattr(self, method):
            getattr(self, method)(msg, *matcher.groups)
            return True

        # no matches, so this message is not
        # for us; allow processing to continue
        return False
      
    # admin utility!
    def createvillage(self, msg, village=DEFAULT_VILLAGE):
        village = village.strip()
        try:
            # TODO: add administrator authentication
            print "REPORTER:CREATEVILLAGE"
            ville = Village.objects.get_or_create(name=village)
            msg.respond( _("village %s created") % (village) )
            return
            # TODO: remove this for production
        except:
            msg.respond(
                _("register-fail") 
            )
             
    def register_name(self, msg, family_name):
        try:
            msg.sender.family_name = family_name
            msg.sender.save()
            print( _("Hello %s!") % family_name )
            msg.respond( _("Hello %s!") % family_name )
        except:
            print( _("register-fail") )
            msg.respond( _("register-fail") )

    def join(self, msg, village=DEFAULT_VILLAGE):
        try:
            # parse the name, and create a contact
            print "REPORTER:JOIN"
            villes = Village.objects.filter(name=village)
            if len(villes)==0:
                # TODO: when this scales up, show 3 most similar village names
                all_villes = Village.objects.all()[:2]
                resp =  _( ("I do not recognize %s. Please txt: #join VILLAGE_NAME") % village ) 
                if all_villes is not None:
                    resp = ("%s %s") % (resp, _("where VILLAGE_NAME is") )
                    for i in all_villes:
                        resp = ("%s %s") % (resp, i.name) 
                msg.respond(resp)
                return msg.sender
            ville = villes[0]
            #create new membership
            msg.sender.add_to_group(ville)
            print( _("first-login") % {"village": village } )
            msg.respond( _("first-login") % {"village": village } )
            return msg.sender
        except:
            print( _("register-fail") )
            msg.respond( _("register-fail") )
            
 
    def blast(self, msg, txt):
        txt = txt.strip()
        try:
            sender = msg.sender
            if sender is None:
                #join default village and send to default village
                sender = self.join(msg)
            print "REPORTER:BLAST"
            #find all reporters from the same location
            villages = VillagesForContact(sender)
            if len(villages)==0:
                print _("You must join a village before sending messages")
                msg.respond( _("You must join a village before sending messages") )
                return
            village_names = ''
            for ville in villages:
                village_names = ("%s %s") % (village_names, ville.name) 
                recipients = ville.flatten()
                
                # it makes sense to complete all of the sending
                # before sending the confirmation sms
                # iterate every member of the group we are broadcasting
                # to, and queue up the same message to each of them
                for recipient in recipients:
                    if int(recipient.id) != int(sender.id):
                        #add signature
                        anouncement = _("%s - sent to [%s] from %s") % ( txt, ville.name, sender.signature() )
                        #todo: limit chars to 1 txt message?
                        conns = ChannelConnection.objects.all().filter(contact=recipient)
                        for conn in conns:
                            # todo: what is BE is gone? Use different one?
                            print "SENDING ANNOUNCEMENT TO: %s VIA: %s" % (conn.user_identifier,conn.communication_channel.slug)
                            be = self.router.get_backend(conn.communication_channel.slug)
                            be.message(conn.user_identifier, anouncement).send()
                        
            village_names = village_names.strip()
            print( _("success! %s recvd msg: %s") % (village_names,txt) ) 
            msg.respond( _("success! %s recvd msg: %s") % (village_names,txt) ) 
            return sender
        except:
            traceback.print_exc()
            msg.respond(
                _("blast-fail") 
            )
        

    def leave(self, msg):
        try:
            print "REPORTER:LEAVE"
            if msg.sender is not None:
                villages=VillagesForContact(msg.sender)
                if len(villages)>0:
                    #default to deleting all persistent connections with the same identity
                    #we can always come back later and make sure we are deleting the right backend
                    for ville in villages:
                        msg.sender.delete()
                        msg.respond(
                            _("leave-success") % { "village": ville })
                    return
            msg.respond( _("nothing to leave") )
            return
        # something went wrong - at the
        # moment, we don't care what
        except:
            msg.respond(
                _("leave-fail") 
            )
    

                    
    def lang(self, msg, code):
        # TODO: make this a decorator to be used in all functions
        # so that users don't have to register in order to get going
        print "REPORTER:LANG"
        err = None
        if msg.sender is None:
            err = _("denied")
            msg.sender = self.join(msg)
        
        # if the language code was valid, save it
        # TODO: obviously, this is not cross-app
        if code in self.SUPPORTED_LANGUAGES:
            msg.sender.set_locale(code)
            msg.sender.save()
            self.__setLocale(code)
            print _("lang-set")
            resp = _("lang-set")
        
        # invalid language code. don't do
        # anything, just send an error message
        else: resp = _("bad-lang")
        
        # always send *some*
        # kind of response
        
        if err is not None:
            resp = ("%s %s.") % (resp,err)       
        msg.respond( resp )
    
    def __loadFixtures(self):
         Village.objects.get_or_create(name=DEFAULT_VILLAGE)
         
    def __initTranslators(self):
        self.translators = {}
        path = os.path.join(os.path.dirname(__file__),"locale")
        for lang in self.SUPPORTED_LANGUAGES:
            trans = gettext.translation(lang,path,[lang])
            self.translators.update( {lang:trans} )
        self.translators[DEFAULT_LANGUAGE].install()

    def __setLocale(self, locale):
        if locale is not None:
            self.translators[locale].install()
        else: 
            self.translators[DEFAULT_LANGUAGE].install()

