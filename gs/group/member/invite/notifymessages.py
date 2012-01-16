# coding=utf-8
from urllib import urlencode
from zope.cachedescriptors.property import Lazy
from gs.group.base.page import GroupPage
from gs.profile.email.base.emailuser import EmailUser
UTF8 = 'utf-8'

class InvitationMessage(GroupPage):
    @Lazy
    def subject(self):
      retval = u'Invitation to join %s (Action required)' % \
        self.groupInfo.name
      return retval
      
    @Lazy
    def supportEmail(self):
        msg = u'Hi!\n\nI received an invitation to join the group '\
            u'%s\n    %s\nand...' % \
            (self.groupInfo.name, self.groupInfo.url)
        data = {
          'Subject':  self.subject.encode(UTF8),
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
        
    @Lazy
    def defaultMessage(self):
        retval = u'''<p style="margin: 1.385em 0 1.385em 1.385em;">
        Please accept this invitation to join %s. I
        have set up a profile for you, so you can start participating
        in the group as soon as you accept this 
        invitation.</p>''' % self.groupInfo.name
        return retval.encode(UTF8)

    
class InvitationMessageText(InvitationMessage):
    def __init__(self, context, request):
        InvitationMessage.__init__(self, context, request)
        response = request.response
        response.setHeader("Content-Type", 'text/plain; charset=UTF-8')
        filename = 'invitation-to-%s.txt' % self.groupInfo.name
        response.setHeader('Content-Disposition',
                            'inline; filename="%s"' % filename)

    @Lazy
    def defaultMessage(self):
        retval = u'    Please accept this invitation to join %s.\n' \
            u'    I have set up a profile for you, so you can start '\
            u'participating\n    in the group as soon as you accept '\
            u'this invitation.' % self.groupInfo.name
        return retval.encode(UTF8)

