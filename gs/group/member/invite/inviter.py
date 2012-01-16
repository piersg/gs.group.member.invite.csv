# coding=utf-8
from operator import concat
from time import asctime
import md5
from zope.cachedescriptors.property import Lazy
from Products.XWFCore.XWFUtils import convert_int2b62
from gs.profile.notify.interfaces import IGSNotifyUser
from gs.profile.email.base.emailuser import EmailUser
from queries import InvitationQuery
from notify import InvitationNotifier

class Inviter(object):
    def __init__(self, context, request, userInfo, adminInfo, siteInfo, groupInfo):
        self.context = context
        self.request = request
        self.userInfo = userInfo
        self.adminInfo = adminInfo
        self.siteInfo = siteInfo
        self.groupInfo = groupInfo
        
    @Lazy
    def invitationQuery(self):
        da = self.context.zsqlalchemy
        retval = InvitationQuery(da)
        return retval

    def create_invitation(self, data, initial):
        inviteId = self.new_invitation_id(data)
        self.invitationQuery.add_invitation(inviteId, self.siteInfo.id,
            self.groupInfo.id, self.userInfo.id, self.adminInfo.id, initial)
        return inviteId

    def new_invitation_id(self, data):
        miscStr = reduce(concat, [unicode(i).encode('ascii', 'xmlcharrefreplace') 
                                    for i in data.values()], '')
        istr = asctime() + self.siteInfo.id + \
                unicode(self.siteInfo.name).encode('ascii', 'xmlcharrefreplace') +\
                self.groupInfo.id + \
                unicode(self.groupInfo.name).encode('ascii', 'xmlcharrefreplace') +\
                self.userInfo.id + \
                unicode(self.userInfo.name).encode('ascii', 'xmlcharrefreplace') +\
                self.adminInfo.id + \
                unicode(self.adminInfo.name).encode('ascii', 'xmlcharrefreplace') +\
                miscStr
        inum = long(md5.new(istr).hexdigest(), 16)
        retval = str(convert_int2b62(inum))
        assert retval
        assert type(retval) == str
        return retval
        
    def send_notification(self, subject, message, inviteId, fromAddr, toAddr=''):
        mfrom = fromAddr.strip()
        toAddrs = self.get_addrs(toAddr)
        self.notifier.notify(self.adminInfo, self.userInfo, fromAddr, 
                                toAddrs, inviteId, subject, message)
        
    @Lazy
    def notifier(self):
        retval = InvitationNotifier(self.context, self.request)
        return retval

    def get_addrs(self, toAddr):
        notifiedUser = IGSNotifyUser(self.userInfo)            
        try:
            addrs = notifiedUser.get_addresses()
        except AssertionError, assErr:
            addrs = [toAddr.strip()]
        addrs = [a for a in addrs if a]
        ### BEGIN(hack)
        ### TODO: Remove this hack
        ###
        ### --=mpj17=-- UGLY HACK --=mpj17=--
        ###
        ### Sometimes a person is invited who has an existing profile
        ### but all his or her email addresses are unverified. If this 
        ### is the case we will send the invitation anyway. With **luck**
        ### the user will only have **one** (un, uno, I, 1) address,
        ### which will get verified when he or she joins. Otherwise the
        ### gs.profile.invite.initialresponse.InitialResponseForm may
        ### verify the **wrong** address.
        ###
        ### See <https://projects.iopen.net/groupserver/ticket/514>
        ###
        if not addrs:
            eu = EmailUser(self.context, self.userInfo)
            addrs = eu.get_addresses()
        ### END(hack) (* Modula-2 Geek *)
        assert type(addrs) == list,\
            'Returning a %s, rather than a list' % type(addrs)
        return addrs

