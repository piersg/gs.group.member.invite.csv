# coding=utf-8
try:
    from five.formlib.formbase import PageForm
except ImportError:
    from Products.Five.formlib.formbase import PageForm
    
from zope.component import createObject
from zope.formlib import form
from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile
from Products.CustomUserFolder.userinfo import userInfo_to_anchor
from Products.GSProfile.edit_profile import multi_check_box_widget
from Products.XWFCore.XWFUtils import get_the_actual_instance_from_zope
from gs.content.form.radio import radio_widget
from interfaces import IGSInviteSiteMembers
from inviter import Inviter
from audit import Auditor, INVITE_NEW_USER, INVITE_OLD_USER

class GSInviteSiteMembersForm(PageForm):
    label = u'Invite Site Members'
    pageTemplateFileName = 'browser/templates/invitesitemembers.pt'
    template = ZopeTwoPageTemplateFile(pageTemplateFileName)

    def __init__(self, context, request):
        PageForm.__init__(self, context, request)
        self.siteInfo = createObject('groupserver.SiteInfo', context)
        self.__formFields = self.__adminInfo = self.__groupInfo = None

    @property
    def groupInfo(self):
        if self.__groupInfo == None:
            self.__groupInfo = \
                createObject('groupserver.GroupInfo', self.context)
        return self.__groupInfo

    @property
    def form_fields(self):
        if self.__formFields == None:
            self.__formFields = form.Fields(IGSInviteSiteMembers,
                render_context=False)
            self.__formFields['site_members'].custom_widget = \
                multi_check_box_widget
            self.__formFields['delivery'].custom_widget = radio_widget
        return self.__formFields
        
    @property
    def adminInfo(self):
        if self.__adminInfo == None:
            self.__adminInfo = createObject('groupserver.LoggedInUser', 
                self.context)
        return self.__adminInfo

    @property
    def defaultFromEmail(self):
        retval = self.adminInfo.user.get_preferredEmailAddresses()[0]
        return retval
        
    def setUpWidgets(self, ignore_request=False):
        data = {'fromAddr': self.defaultFromEmail,
                'delivery': 'email'}
        subject = u'An Invitation to Join %s' % self.groupInfo.name
        data['subject'] = subject
        
        message = u'''Hi there!

Please accept this invitation to join %s. Everything is 
ready to go, so you can start participating in the group as soon as you 
click the link below and accept this invitation.''' % self.groupInfo.name
        data['message'] = message
        
        self.widgets = form.setUpWidgets(
            self.form_fields, self.prefix, self.context,
            self.request, form=self, data=data,
            ignore_request=ignore_request)

    @form.action(label=u'Invite', failure='handle_invite_action_failure')
    def handle_invite(self, action, data):
        for userId in data['site_members']:
            ctx = get_the_actual_instance_from_zope(self.context)
            userInfo = createObject('groupserver.UserFromId', ctx,
                                        userId)                                    
            inviter = Inviter(ctx, self.request, userInfo, 
                        self.adminInfo, self.siteInfo, self.groupInfo)
            inviteId = inviter.create_invitation(data, False)
            auditor = Auditor(self.siteInfo, self.groupInfo, 
                        self.adminInfo, userInfo)
            auditor.info(INVITE_OLD_USER)
            inviter.send_notification(data['subject'],  data['message'], 
                inviteId, data['fromAddr'])
            
            self.status = '%s\n<li>%s</li>' %\
                            (self.status, userInfo_to_anchor(userInfo))
            
            self.set_delivery(userInfo, data['delivery'])
            
        self.status = u'<p>Invited the following users to '\
          u'join <a class="fn" href="%s">%s</a></p><ul>%s</ul>' %\
            (self.groupInfo.url, self.groupInfo.name, self.status)

        if not(data['site_members']):
            self.status = u'<p>No site members were selected.</p>'
        assert self.status
        assert type(self.status) == unicode

    def handle_invite_action_failure(self, action, data, errors):
        if len(errors) == 1:
            self.status = u'<p>There is an error:</p>'
        else:
            self.status = u'<p>There are errors:</p>'

    def set_delivery(self, userInfo, delivery):
        if delivery == 'email':
            # --=mpj17=-- The default is one email per post
            pass
        elif delivery == 'digest':
            userInfo.user.set_enableDigestByKey(self.groupInfo.id)
        elif delivery == 'web':
            userInfo.user.set_disableDeliveryByKey(self.groupInfo.id)

