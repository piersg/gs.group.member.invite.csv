# coding=utf-8
from zope.component import createObject, getMultiAdapter
from zope.cachedescriptors.property import Lazy
from gs.profile.notify.sender import MessageSender
UTF8 = 'utf-8'

class InvitationNotifier(object):
    textTemplateName = 'invitationmessage.txt'
    htmlTemplateName = 'invitationmessage.html'
    
    def __init__(self, context, request):
        self.context = context
        self.request = request

    @Lazy
    def groupInfo(self):
        retval = createObject('groupserver.GroupInfo', self.context)
        assert retval, 'Could not create the GroupInfo from %s' % self.context
        return retval
        
    @Lazy
    def loggedInUserInfo(self):
        retval = createObject('groupserver.LoggedInUser', self.context)
        assert retval, 'Could not create the user-info for the logged '\
            'in user from %s' % self.context
        return retval

    @Lazy
    def textTemplate(self):
        retval = getMultiAdapter((self.context, self.request), 
                    name=self.textTemplateName)
        assert retval
        return retval

    @Lazy
    def htmlTemplate(self):
        retval = getMultiAdapter((self.context, self.request), 
                    name=self.htmlTemplateName)
        assert retval
        return retval
        
    def notify(self, userInfo):
        subject = (u'Welcome to %s' % (self.groupInfo.name).encode(UTF8))
        text = self.textTemplate(userInfo=userInfo)
        html = self.htmlTemplate(userInfo=userInfo)
        ms = MessageSender(self.context, userInfo)
        ms.send_message(subject, text, html)

