# coding=utf-8
from operator import concat
import md5
from time import asctime
from zope.contentprovider.tales import addTALNamespaceData
from Products.XWFCore.XWFUtils import convert_int2b62
from gs.profile.notify.interfaces import IGSNotifyUser
from gs.profile.notify.adressee import Addressee, SupportAddressee
from queries import InvitationQuery
from utils import invite_id
from invitationmessagecontentprovider import InvitationMessageContentProvider
from createinvitation import create_invitation_message

class Inviter(object):
    def __init__(self, context, request, userInfo, adminInfo, siteInfo, groupInfo):
        self.context = context
        self.request = request
        self.userInfo = userInfo
        self.adminInfo = adminInfo
        self.siteInfo = siteInfo
        self.groupInfo = groupInfo
        self.__invitationQuery = self.__contentProvider = None
        
    @property
    def invitationQuery(self):
        if self.__invitationQuery == None:
            da = self.context.zsqlalchemy
            self.__invitationQuery = InvitationQuery(da)
        return self.__invitationQuery

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
    
    @property
    def contentProvider(self):
        if self.__contentProvider == None:
            self.__contentProvider = \
                InvitationMessageContentProvider(self.context, self.request, self)
            self.context.vars = {} # --=mpj17=-- Ask me no questions\ldots
            addTALNamespaceData(self.__contentProvider, self.context) # I tell you no lies.
        return self.__contentProvider
        
    def send_notification(self, subject, message, inviteId, fromAddr, toAddr=''):
        mfrom = fromAddr.strip()
        notifiedUser = IGSNotifyUser(self.userInfo)            
        for mto in self.get_addrs(toAddr):
            assert mto, 'No to address for %s (%s)' % \
                (self.userInfo.name, self.userInfo.id)
            assert mfrom, 'No from address' 
            msg = create_invitation_message(
                    Addressee(self.adminInfo, mfrom),
                    Addressee(self.userInfo, mto), 
                    SupportAddressee(self.context, self.siteInfo), 
                    subject, message, inviteId, self.contentProvider)
            notifiedUser.send_message(msg, mto, mfrom)

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
        ### Sometimes a persion is invited who has an existing profile
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
            addrs = self.userInfo.user.get_emailAddresses()
        ### END(hack) (* Modula-2 Geek *)
        return addrs

