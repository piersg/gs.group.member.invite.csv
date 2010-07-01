# coding=utf-8
from queries import InvitationQuery
from utils import invite_id
from invitationmessagecontentprovider import InvitationMessageContentProvider
from createinvitation import create_invitation_message

class Inviter(object):
    def __init__(self, context, request, userInfo, adminInfo, groupInfo):
        self.context = context
        self.request = request
        self.userInfo = userInfo
        self.adminInfo = adminInfo
        self.groupInfo = groupInfo
        self.__invitationQuery = self.__contentProvider = None
        
    @property
    def invitationQuery(self):
        if self.__invitationQuery == None:
            da = self.context.zsqlalchemy
            self.__invitationQuery = InvitationQuery(da)
        return self.__invitationQuery

    def create_invitation(self, data, initial):
        miscStr = reduce(concat, [unicode(i).encode('ascii', 'xmlcharrefreplace') 
                                    for i in data.values()], '')
        inviteId = invite_id(self.siteInfo.id, self.groupInfo.id, 
            self.adminInfo.id, miscStr)
        self.invitationQuery.add_invitation(inviteId, self.siteInfo.id,
            self.groupInfo.id, self.userInfo.id, self.adminInfo.id, initial)
        return inviteId

    @property
    def contentProvider(self):
        if self.__contentProvider == None:
            self.__contentProvider = \
                InvitationMessageContentProvider(self.context, self.request, self)
            self.vars = {} # --=mpj17=-- Ask me no questions\ldots
            addTALNamespaceData(self.__contentProvider, self.context) # I tell you no lies.
        return self.__contentProvider
        
    def send_notification(self, subject, message, inviteId, fromAddr, toAddr=''):
        mfrom = fromAddr.strip()
        
        notifiedUser = IGSNotifyUser(self.userInfo)            
        addrs = notifiedUser.get_addresses()
        if not(addrs):
            # A new user, without any verified email addresses.
            addrs = [toAddr.strip()]
            assert addrs, 'To address for a new user not set.'
            
        for mto in addrs:
            msg = create_invitation_message(
                    Addressee(self.adminInfo, mfrom),
                    Addressee(self.userInfo, mto), 
                    SupportAddressee(self.context, self.siteInfo), 
                    subject, message, inviteId, self.contentProvider)
            notifiedUser.send_message(msg, mto, mfrom)

