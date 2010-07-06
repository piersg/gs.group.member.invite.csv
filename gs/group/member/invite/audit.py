# coding=utf-8
from pytz import UTC
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape
from base64 import b64decode
from zope.component import createObject
from zope.component.interfaces import IFactory
from zope.interface import implements, implementedBy
from Products.CustomUserFolder.interfaces import IGSUserInfo
from Products.CustomUserFolder.userinfo import userInfo_to_anchor
from Products.GSGroup.groupInfo import groupInfo_to_anchor
from Products.GSAuditTrail import IAuditEvent, BasicAuditEvent, \
  AuditQuery, event_id_from_data
from Products.XWFCore.XWFUtils import munge_date

SUBSYSTEM = 'gs.group.member.invite'
import logging
log = logging.getLogger(SUBSYSTEM) #@UndefinedVariable

UNKNOWN                 = '0'
INVITE_NEW_USER         = '1'
INVITE_OLD_USER         = '2'
INVITE_EXISTING_MEMBER  = '3'

class AuditEventFactory(object):
    implements(IFactory)

    title=u'User Profile Invitation Audit-Event Factory'
    description=u'Creates a GroupServer audit event for invitations'

    def __call__(self, context, event_id,  code, date,
        userInfo, instanceUserInfo,  siteInfo,  groupInfo,
        instanceDatum='', supplementaryDatum='', subsystem=''):

        if (code == INVITE_NEW_USER):
            event = InviteNewUserEvent(context, event_id, date, 
              userInfo, instanceUserInfo, siteInfo, groupInfo,
              instanceDatum, supplementaryDatum)
        elif (code == INVITE_OLD_USER):
            event = InviteOldUserEvent(context, event_id, date, 
              userInfo, instanceUserInfo, siteInfo, groupInfo,
              instanceDatum, supplementaryDatum)
        elif (code == INVITE_EXISTING_MEMBER):
            event = InviteExistingMemberEvent(context, event_id, date, 
              userInfo, instanceUserInfo, siteInfo, groupInfo,
              instanceDatum, supplementaryDatum)
        else:
            event = BasicAuditEvent(context, event_id, UNKNOWN, date, 
              userInfo, instanceUserInfo, siteInfo, groupInfo, 
              instanceDatum, supplementaryDatum, SUBSYSTEM)
        assert event
        return event
    
    def getInterfaces(self):
        return implementedBy(BasicAuditEvent)

class InviteNewUserEvent(BasicAuditEvent):
    """Administrator inviting a New User Event. 
    
    The "instanceDatum" is the address used to create the new user.
    """
    implements(IAuditEvent)

    def __init__(self, context, id, d, userInfo, instanceUserInfo, 
        siteInfo, groupInfo, instanceDatum,  supplementaryDatum):
        
        BasicAuditEvent.__init__(self, context, id, 
          INVITE_NEW_USER, d, userInfo, instanceUserInfo, 
          siteInfo, groupInfo,  instanceDatum, supplementaryDatum, 
          SUBSYSTEM)
    
    def __str__(self):
        retval = u'Administrator %s (%s) inviting a new user %s (%s) '\
          u'with address <%s> to join %s (%s) on %s (%s)' %\
          (self.userInfo.name, self.userInfo.id,
          self.instanceUserInfo.name, self.instanceUserInfo.id,  
          self.instanceDatum,
          self.groupInfo.name, self.groupInfo.id,
          self.siteInfo.name, self.siteInfo.id)
        return retval.encode('ascii', 'ignore')

    @property
    def xhtml(self):
        cssClass = u'audit-event profile-invite-event-%s' % self.code
        email = u'<code class="email">%s</code>' % self.instanceDatum
        retval = u'<span class="%s">Invited the new user %s (with the '\
            u'email address %s) to join %s.</span>' %\
            (cssClass, userInfo_to_anchor(self.instanceUserInfo),
            groupInfo_to_anchor(self.groupInfo))
        if ((self.instanceUserInfo.id != self.userInfo.id)
            and not(self.userInfo.anonymous)):
            retval = u'%s &#8212; %s' %\
              (retval, userInfo_to_anchor(self.userInfo))
        return retval

class InviteOldUserEvent(BasicAuditEvent):
    """Administrator Inviting an old User Event. 
    
    The "instanceDatum" is the address used to match the old user.
    """
    implements(IAuditEvent)

    def __init__(self, context, id, d, userInfo, instanceUserInfo, 
        siteInfo, groupInfo, instanceDatum,  supplementaryDatum):
        
        BasicAuditEvent.__init__(self, context, id, 
          INVITE_OLD_USER, d, userInfo, instanceUserInfo, 
          siteInfo, groupInfo, instanceDatum, supplementaryDatum, 
          SUBSYSTEM)
    
    def __str__(self):
        retval = u'Administrator %s (%s) inviting an existing user '\
          u'%s (%s) with address <%s> to join %s (%s) on %s (%s)' %\
          (self.userInfo.name, self.userInfo.id,
          self.instanceUserInfo.name, self.instanceUserInfo.id,  
          self.instanceDatum,
          self.groupInfo.name, self.groupInfo.id,
          self.siteInfo.name, self.siteInfo.id)
        return retval.encode('ascii', 'ignore')

    @property
    def xhtml(self):
        cssClass = u'audit-event profile-invite-event-%s' % self.code
        email = u'<code class="email">%s</code>' % self.instanceDatum
        retval = u'<span class="%s">Invited the existing user %s to '\
            u'join %s.</span>' %\
            (cssClass, userInfo_to_anchor(self.instanceUserInfo),
            groupInfo_to_anchor(self.groupInfo))
        if ((self.instanceUserInfo.id != self.userInfo.id)
            and not(self.userInfo.anonymous)):
            retval = u'%s &#8212; %s' %\
              (retval, userInfo_to_anchor(self.userInfo))
        return retval

class InviteExistingMemberEvent(BasicAuditEvent):
    """Administrator Inviting an Existing Group Member. 
    
    The "instanceDatum" is the address used to match the existing group
    member.
    """
    implements(IAuditEvent)

    def __init__(self, context, id, d, userInfo, instanceUserInfo, 
        siteInfo, groupInfo, instanceDatum,  supplementaryDatum):
        
        BasicAuditEvent.__init__(self, context, id, 
          INVITE_OLD_USER, d, userInfo, instanceUserInfo, 
          siteInfo, groupInfo, instanceDatum, supplementaryDatum, 
          SUBSYSTEM)
    
    def __str__(self):
        retval = u'Administrator %s (%s) tried to invite an existing '\
          u'group member %s (%s) with address <%s> to join %s (%s) '\
          u'on %s (%s)' %\
          (self.userInfo.name, self.userInfo.id,
          self.instanceUserInfo.name, self.instanceUserInfo.id,  
          self.instanceDatum,
          self.groupInfo.name, self.groupInfo.id,
          self.siteInfo.name, self.siteInfo.id)
        return retval.encode('ascii', 'ignore')

    @property
    def xhtml(self):
        cssClass = u'audit-event profile-invite-event-%s' % self.code
        email = u'<code class="email">%s</code>' % self.instanceDatum
        retval = u'<span class="%s">Tried to invite the existing member '\
            u' %s to join %s.</span>' %\
            (cssClass, userInfo_to_anchor(self.instanceUserInfo),
            groupInfo_to_anchor(self.groupInfo))
        if ((self.instanceUserInfo.id != self.userInfo.id)
            and not(self.userInfo.anonymous)):
            retval = u'%s &#8212; %s' %\
              (retval, userInfo_to_anchor(self.userInfo))
        return retval
        
class Auditor(object):
    def __init__(self, siteInfo, groupInfo, adminInfo, userInfo):
        self.siteInfo  = siteInfo
        self.groupInfo = groupInfo
        self.adminInfo = adminInfo
        self.userInfo  = userInfo
        
        da = userInfo.user.zsqlalchemy
        self.queries = AuditQuery(da)
      
        self.factory = AuditEventFactory()
        
    def info(self, code, instanceDatum = '', supplementaryDatum = ''):
        d = datetime.now(UTC)
        eventId = event_id_from_data(self.adminInfo, self.userInfo,
            self.siteInfo, code, instanceDatum, supplementaryDatum)
          
        e = self.factory(self.userInfo.user, eventId,  code, d, 
                self.adminInfo,  self.userInfo, self.siteInfo, 
                self.groupInfo, instanceDatum, supplementaryDatum, 
                SUBSYSTEM)
          
        self.queries.store(e)
        log.info(e)

