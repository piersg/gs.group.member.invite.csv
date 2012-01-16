# coding=utf-8
from urllib import urlencode
from zope.cachedescriptors.property import Lazy
from gs.group.base.page import GroupPage
from gs.profile.email.base.emailuser import EmailUser
UTF8 = 'utf-8'

def default_message(groupInfo):
    return u'Please accept this invitation to join %s. I have set '\
        u'up a profile for you, so you can start participating in '\
        u'the group as soon as you accept this  invitation.' % \
        groupInfo.name

def default_subject(groupInfo):
    return u'Invitation to join %s (Action required)' % groupInfo.name

class InvitationMessage(GroupPage):
    @Lazy
    def supportEmail(self):
        sub = (u'Invitation to %s' % self.groupInfo.name).encode(UTF8)
        msg = (u'Hi!\n\nI received an invitation to join the group '\
            u'%s\n    %s\nand...' % (self.groupInfo.name, 
                self.groupInfo.url)).encode(UTF8)
        data = {
          'Subject':  sub,
          'body':     msg,
        }
        retval = 'mailto:%s?%s' % \
            (self.siteInfo.get_support_email(), urlencode(data))
        return retval
    
    def get_addr(self, userInfo):
        eu = EmailUser(self.context, userInfo)
        a = eu.get_verified_addresses()
        retval = (a and a[0]) or eu.get_addresses()[0]
        assert retval
        return retval
    
    def format_message(self, m):
        return FormattedMessage(m).html
    
    @Lazy
    def defaultSubject(self):
        return default_subject(groupInfo)
    
    @Lazy
    def defaultMessage(self):
        retval = default_message(self.groupInfo)
        return retval.encode(UTF8)

    
class InvitationMessageText(InvitationMessage):
    def __init__(self, context, request):
        InvitationMessage.__init__(self, context, request)
        response = request.response
        response.setHeader("Content-Type", 'text/plain; charset=UTF-8')
        filename = 'invitation-to-%s.txt' % self.groupInfo.name
        response.setHeader('Content-Disposition',
                            'inline; filename="%s"' % filename)

    def format_message(self, m):
        return FormattedMessage(m).txt
        
class FormattedMessage(object):
    def __init__(self, message):
      self.originalMessage = message
      
    @Lazy
    def html(self):
        p = '<p style="margin: 1.385em 0 1.385em 1.385em;">'
        withPara = self.originalMessage.replace(u'\n\n', u'</p>%s' % p)
        withBr = withPara.replace('u\n', u'<br/>')
        retval = '%s%s</p>' % (p, withBr)
        return retval

    @Lazy
    def txt(self):
        tw = TextWrapper(initial_indent = 4, subsequent_indent = 4)
        retval = ''
        for line in self.originalMessage.splitlines():
            p = tw.wrap(line.strip())
            retval = '%s%s\n\n' % (retval, p)
        retval = retval.strip()
        return retval

