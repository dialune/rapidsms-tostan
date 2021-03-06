#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save
from django.template.loader import render_to_string
from rapidsms.webui.settings import RAPIDSMS_APPS as app_conf

#this is hacky until the email backend is incorporated fully
from apps.logtracker.email import EmailAgent

class LogTrack(models.Model):
    """
    LogTrack is a verbose means to store any arbitrary log information 
    into a python model.
    
    Using the admin.py as the way to instantiate the handler, all log messages 
    will be stored with all relevant data into the database.
    """        
    level = models.IntegerField(null=True)
    channel = models.CharField(max_length=128, null=True)
    created = models.DateTimeField(auto_now_add=True)
    message = models.TextField(null=True)    
    pathname = models.TextField(null=True)
    funcname = models.CharField(max_length=128,null=True)
    module = models.CharField(max_length=128,null=True)
    filename = models.CharField(max_length=128, null=True)
    line_no = models.IntegerField(null=True)    
    traceback = models.TextField(null=True)
    
    #when you do a logging message:
    #logging.debug('something interesting, extra={}
    #the extra kwarg should be a dictionary
    #anytime you add a new item to the extra dictionary, 
    # it will be assigned to the LogRecord 
    # object as a property
    #(just be careful to not use a reserved/in use LogRecord object
    #So, if you want to save some important local variable/state information for your error
    #it's easier to extract the information by finding  
    data_dump = models.TextField(null=True)
    
    def __unicode__(self):
        return self.message
    class Meta:
        verbose_name = _("Log Tracker")


# Signal registration is done here in the models instead of the views because
# everytime someone hits a view and that messes up the process registration
# whereas models is loaded once
def sendAlert(sender, instance, created, *args, **kwargs): #get sender, instance, created    
    # only send emails on newly created logs, not all of them
    if not created:
        return 
    
    #set a global threshold to say if anything is a logging.ERROR, chances are
    #we always want an alert.
    if instance.level >= int(app_conf['logtracker']['alert_threshold']):
        context = {}
        context['log'] = instance
        try:
            rendered_text = render_to_string("logtracker/alert_display.html", context)
        except Exception, e:
            # quick hack: avoid using 'render_to_string' since it doesn't quite work with the current
            # rapidsms i18n mechanism

            # we generally cannot allow errors to be raised in this function
            # because it throws logtracker into an infinite loop

            rendered_text = "MESSAGE: %s<br\>PATH: %s<br\>LINE NUMBER: %s<br\>DATA: %s" % \
                            (instance.message, instance.pathname, 
                             instance.line_no, instance.data_dump)
        
        
        # Send it to an email address baked into the settings/ini file.
        # restrict the subject to 78 characters to comply with the RFC
        title = ("[Tostan Alert] " + instance.message)[:78]
        # newlines makey title mad
        title = title.replace("\n", ",")
        eml = EmailAgent()
        eml.send_email(title,
                       app_conf['logtracker']['default_alert_email'], 
                       rendered_text)
            
# Register to receive signals from LogTrack
post_save.connect(sendAlert, sender=LogTrack)
