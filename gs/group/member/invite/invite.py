# coding=utf-8
'''The form that allows an admin to invite a new person to join a group.'''
from operator import concat
from zope.component import createObject
from zope.formlib import form
from zope.contentprovider.tales import addTALNamespaceData
from Products.Five.formlib.formbase import PageForm
from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile
from Products.CustomUserFolder.interfaces import IGSUserInfo
from Products.CustomUserFolder.userinfo import userInfo_to_anchor
from Products.GSGroup.groupInfo import groupInfo_to_anchor
from Products.GSGroupMember.groupmembership import \
  user_member_of_group, user_admin_of_group
from Products.GSProfile.edit_profile import select_widget, wym_editor_widget
from Products.GSProfile.utils import create_user_from_email, \
    enforce_schema
from Products.GSProfile.emailaddress import NewEmailAddress, \
    EmailAddressExists
from Products.GSGroup.changebasicprivacy import radio_widget
from gs.profile.notify.interfaces import IGSNotifyUser
from gs.profile.notify.adressee import Addressee, SupportAddressee
from queries import InvitationQuery
from utils import set_digest, invite_to_groups, invite_id
from invitefields import InviteFields
from audit import Auditor, INVITE_NEW_USER, INVITE_OLD_USER
from invitationmessagecontentprovider import InvitationMessageContentProvider
from createinvitation import create_invitation_message

class InviteEditProfileForm(PageForm):
    label = u'Invite a New Group Member'
    pageTemplateFileName = 'browser/templates/edit_profile_invite.pt'
    template = ZopeTwoPageTemplateFile(pageTemplateFileName)

    def __init__(self, context, request):
        PageForm.__init__(self, context, request)

        siteInfo = self.siteInfo = \
          createObject('groupserver.SiteInfo', context)
        self.__groupInfo = self.__formFields =  self.__config = None
        self.__adminInfo = self.__invitationQuery = None
        self.inviteFields = InviteFields(context)

    @property
    def form_fields(self):
        if self.__formFields == None:
            self.__formFields = form.Fields(self.inviteFields.adminInterface, 
                render_context=False)
            tz = self.__formFields['tz']
            tz.custom_widget = select_widget
            self.__formFields['biography'].custom_widget = wym_editor_widget
            self.__formFields['delivery'].custom_widget = radio_widget
        return self.__formFields
        
    def setUpWidgets(self, ignore_request=False):
        data = {}

        siteTz = self.siteInfo.get_property('tz', 'UTC')
        defaultTz = self.groupInfo.get_property('tz', siteTz)
        data['tz'] = defaultTz

        subject = u'An Invitation to Join %s' % self.groupInfo.name
        data['subject'] = subject
        
        message = u'''Hi there!

Please accept this invitation to join %s. I have set up a profile for
you, so you can start participating in the group as soon as you accept
this invitation.''' % self.groupInfo.name
        data['message'] = message
        
        self.widgets = form.setUpWidgets(
            self.form_fields, self.prefix, self.context,
            self.request, form=self, data=data,
            ignore_request=ignore_request)
        
    @form.action(label=u'Invite', failure='handle_invite_action_failure')
    def handle_invite(self, action, data):
        self.actual_handle_add(action, data)
        
    def handle_invite_action_failure(self, action, data, errors):
        if len(errors) == 1:
            self.status = u'<p>There is an error:</p>'
        else:
            self.status = u'<p>There are errors:</p>'

    # Non-Standard methods below this point
    @property
    def groupInfo(self):
        if self.__groupInfo == None:
            self.__groupInfo = \
                createObject('groupserver.GroupInfo', self.context)
        return self.__groupInfo
        
    @property
    def adminInfo(self):
        if self.__adminInfo == None:
            self.__adminInfo = createObject('groupserver.LoggedInUser', 
                self.context)
        return self.__adminInfo
    
    @property
    def adminWidgets(self):
        return self.inviteFields.get_admin_widgets(self.widgets)

    @property
    def profileWidgets(self):
        return self.inviteFields.get_profile_widgets(self.widgets)    
        
    @property
    def invitationQuery(self):
        if self.__invitationQuery == None:
            da = self.context.zsqlalchemy
            self.__invitationQuery = InvitationQuery(da)
        return self.__invitationQuery
        
    def actual_handle_add(self, action, data):
        acl_users = self.context.acl_users
        toAddr = data['toAddr'].strip()
        
        emailChecker = NewEmailAddress(title=u'Email')
        emailChecker.context = self.context
        e = u'<code class="email">%s</code>' % toAddr
        g = groupInfo_to_anchor(self.groupInfo)
        
        try:
            emailChecker.validate(toAddr)
        except EmailAddressExists, e:
            user = acl_users.get_userByEmail(toAddr)
            assert user, 'User for address <%s> not found' % toAddr
            userInfo = IGSUserInfo(user)
            u = userInfo_to_anchor(userInfo)
            
            if user_member_of_group(user, self.groupInfo):
                self.status=u'''<li>The person with the email address %s 
&#8213; %s &#8213; is already a member of %s.</li>'''% (e, u, g)
                self.status = u'%s<li>No changes have been made.</li>' % \
                  self.status
            else:
                auditor = Auditor(self.siteInfo, self.groupInfo, 
                    self.adminInfo, userInfo)
                self.status=u'''<li>Inviting the existing person with the
email address %s &#8213; %s &#8213; to join %s.</li>'''% (e, u, g)
                #TODO check: invite_to_groups(userInfo, adminInfo, self.groupInfo)
                auditor.info(INVITE_OLD_USER, toAddr)
        else:
            # Email address does not exist, but it is a legitimate address
            user = create_user_from_email(self.context, toAddr)
            userInfo = IGSUserInfo(user)
            self.add_profile_attributes(userInfo, data)
            inviteId = self.create_invitation(userInfo, data)
            auditor = Auditor(self.siteInfo, self.groupInfo, 
                self.adminInfo, userInfo)
            auditor.info(INVITE_NEW_USER, toAddr)
            self.send_notification(userInfo, inviteId, data)
            
            u = userInfo_to_anchor(userInfo)
            self.status = u'''<li>A profile for %s has been created, and
given the email address %s.</li>\n''' % (u, e)
            self.status = u'%s<li>%s has been sent an invitation to '\
              u'join %s.</li>\n' % (self.status, u, g)
        assert user, 'User not created or found'
        assert self.status
        
    def handle_add_action_failure(self, action, data, errors):
        if len(errors) == 1:
            self.status = u'<p>There is an error:</p>'
        else:
            self.status = u'<p>There are errors:</p>'

    def add_profile_attributes(self, userInfo, data):
        enforce_schema(userInfo.user, self.inviteFields.profileInterface)
        fields = self.form_fields.select(*self.inviteFields.profileFieldIds)
        changed = form.applyChanges(userInfo.user, fields, data)
        set_digest(userInfo, self.groupInfo, data)

    # TODO: The following two methods need to be shared with the CSV code
    def create_invitation(self, userInfo, data):
        miscStr = reduce(concat, [unicode(i).encode('ascii', 'xmlcharrefreplace') 
                                    for i in data.values()], '')
        inviteId = invite_id(self.siteInfo.id, self.groupInfo.id, 
            self.adminInfo.id, miscStr)
        self.invitationQuery.add_invitation(inviteId, self.siteInfo.id,
            self.groupInfo.id, userInfo.id, self.adminInfo.id, True)
        return inviteId
        
    def send_notification(self, userInfo, inviteId, data):
        mfrom = data['fromAddr'].strip()
        mto = data['toAddr'].strip()
        cp = InvitationMessageContentProvider(self.context, self.request, self)
        self.vars = {} # --=mpj17=-- Ask me no questions\ldots
        addTALNamespaceData(cp, self.context) # I tell you no lies.
        msg = create_invitation_message(Addressee(self.adminInfo, mfrom), 
            Addressee(userInfo, mto), SupportAddressee(self.context, self.siteInfo), 
            data['subject'], data['message'], inviteId, cp)
        notifiedUser = IGSNotifyUser(userInfo)
        notifiedUser.send_message(msg, mto, mfrom)

