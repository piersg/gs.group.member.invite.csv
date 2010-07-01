# coding=utf-8
from Products.Five.formlib.formbase import PageForm
from zope.component import createObject
from zope.formlib import form
from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile
from Products.CustomUserFolder.userinfo import userInfo_to_anchor
from Products.GSProfile.edit_profile import multi_check_box_widget
from Products.GSGroup.changebasicprivacy import radio_widget
from interfaces import IGSInviteSiteMembers
from inviter import Inviter

class GSInviteSiteMembersForm(PageForm):
    label = u'Invite Site Members'
    pageTemplateFileName = 'browser/templates/invitesitemembers.pt'
    template = ZopeTwoPageTemplateFile(pageTemplateFileName)
    form_fields = form.Fields(IGSInviteSiteMembers, render_context=False)

    def __init__(self, context, request):
        PageForm.__init__(self, context, request)
        self.siteInfo = createObject('groupserver.SiteInfo', context)
        self.groupInfo= createObject('groupserver.GroupInfo', context)

        self.form_fields['site_members'].custom_widget = \
          multi_check_box_widget
        self.form_fields['delivery'].custom_widget = radio_widget
        
    # --=mpj17=--
    # The "form.action" decorator creates an action instance, with
    #   "handle_invite" set to the success handler,
    #   "handle_invite_action_failure" as the failure handler, and adds the
    #   action to the "actions" instance variable (creating it if 
    #   necessary).
    @form.action(label=u'Invite', failure='handle_invite_action_failure')
    def handle_invite(self, action, data):
        adminInfo = createObject('groupserver.LoggedInUser', self.context)

        for userId in data['site_members']:
            userInfo = createObject('groupserver.UserFromId',
                                    self.context, userId)
                                    
            inviter = Inviter(self.context, self.request, userInfo, 
                        adminInfo, self.groupInfo)
            inviteId = inviter.create_invitation(data, False)
            auditor = Auditor(self.siteInfo, self.groupInfo, 
                        adminInfo, userInfo)
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

    def set_delivery(self, userInfo, delivery)
        if delivery == 'email':
            # --=mpj17=-- The default is one email per post
            pass
        elif delivery == 'digest':
            userInfo.user.set_enableDigestByKey(self.groupInfo.id)
        elif delivery == 'web':
            userInfo.user.set_disableDeliveryByKey(self.groupInfo.id)
