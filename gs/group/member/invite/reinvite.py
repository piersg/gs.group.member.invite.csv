# coding=utf-8
'''The form that allows an admin to re-invite a new person to join a group.'''
from zope.component import createObject
from zope.formlib import form
try:
    from five.formlib.formbase import PageForm
except ImportError:
    from Products.Five.formlib.formbase import PageForm
from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile
from Products.CustomUserFolder.userinfo import userInfo_to_anchor
from Products.XWFCore.XWFUtils import get_the_actual_instance_from_zope
from Products.GSGroup.groupInfo import groupInfo_to_anchor
from Products.GSGroupMember.groupMembersInfo import GSGroupMembersInfo
from inviter import Inviter
from audit import Auditor, INVITE_OLD_USER, INVITE_EXISTING_MEMBER
from interfaces import IGSResendInvitation

class ResendInvitationForm(PageForm):
    pageTemplateFileName = 'browser/templates/resend_invite.pt'
    template = ZopeTwoPageTemplateFile(pageTemplateFileName)

    def __init__(self, context, request):
        PageForm.__init__(self, context, request)

        self.siteInfo = \
          createObject('groupserver.SiteInfo', context)
        self.__groupInfo = self.__formFields =  self.__config = None
        self.__userInfo = self.__adminInfo = None
        self.userId = request.form['form.userId']
        self.label = u'Resend Invitation to %s' % self.userInfo.name

    @property
    def form_fields(self):
        if self.__formFields == None:
            self.__formFields = form.Fields(IGSResendInvitation, 
                render_context=False)
        return self.__formFields
        
    @property
    def defaultFromEmail(self):
        retval = self.adminInfo.user.get_preferredEmailAddresses()[0]
        return retval
      
    @property
    def defaultToEmail(self):
        retval = self.userInfo.user.get_emailAddresses()[0]
        return retval
        
    def setUpWidgets(self, ignore_request=False):
        data = {'fromAddr': self.defaultFromEmail,
          'toAddr' : self.defaultToEmail}

        subject = u'Another Invitation to Join %s' % self.groupInfo.name
        data['subject'] = subject
        
        message = u'''Hi %s!

Please accept this follow-up invitation to join %s. As per 
my previous message, I have set up a profile for you, so you can start 
participating in the group as soon as you accept this invitation.''' % \
  (self.userInfo.name, self.groupInfo.name)
        data['message'] = message
        
        self.widgets = form.setUpWidgets(
            self.form_fields, self.prefix, self.context,
            self.request, form=self, data=data,
            ignore_request=ignore_request)
        
    @form.action(label=u'Resend', failure='handle_invite_action_failure')
    def handle_invite(self, action, data):
        self.actual_handle_add(action, data)
        
    def handle_invite_action_failure(self, action, data, errors):
        if len(errors) == 1:
            self.status = u'<p>There is an error:</p>'
        else:
            self.status = u'<p>There are errors:</p>'

    @property
    def groupInfo(self):
        if self.__groupInfo == None:
            self.__groupInfo = \
                createObject('groupserver.GroupInfo', self.context)
        return self.__groupInfo
    
    @property
    def userInfo(self):
        if self.__userInfo == None:
            self.__userInfo = createObject('groupserver.UserFromId',
                self.context, self.userId)
        return self.__userInfo
    
    @property
    def adminInfo(self):
        if self.__adminInfo == None:
            self.__adminInfo = createObject('groupserver.LoggedInUser', 
                self.context)
        return self.__adminInfo
        
    def actual_handle_add(self, action, data):
        e = u'<code class="email">%s</code>' % self.defaultToEmail
        u = userInfo_to_anchor(self.userInfo)
        g = groupInfo_to_anchor(self.groupInfo)
        auditor, inviter = self.get_auditor_inviter()
        membersInfo = GSGroupMembersInfo(self.groupInfo.groupObj)
        if self.userId in [m.id for m in membersInfo.fullMembers]:
            auditor.info(INVITE_EXISTING_MEMBER, self.defaultToEmail)
            self.status=u'''<li>%s (with the email address %s) is 
already a member of %s.</li>'''% (u, e, g)
            self.status = u'%s<li>No changes have been made.</li>' % \
              self.status
        elif self.userId in [m.id for m in membersInfo.invitedMembers]:
            self.status=u'<li>Resending an invitation to %s (with '\
              u'the email address %s) to join %s.</li>'% (u, e, g)
            inviteId = inviter.create_invitation(data, False)
            auditor.info(INVITE_OLD_USER, self.defaultToEmail)
            inviter.send_notification(data['subject'], 
                data['message'], inviteId, data['fromAddr'], data['toAddr'])
        else:
            self.status=u'''<li>Cannot <strong>resend</strong> an   
invitation to %s, because they have not yet been invited to join %s.</li>'''% (u, g)
            self.status = u'%s<li>No changes have been made.</li>' % \
              self.status
        assert self.status
        
    def handle_add_action_failure(self, action, data, errors):
        if len(errors) == 1:
            self.status = u'<p>There is an error:</p>'
        else:
            self.status = u'<p>There are errors:</p>'

    def get_auditor_inviter(self):
        ctx = get_the_actual_instance_from_zope(self.context)
        inviter = Inviter(ctx, self.request, self.userInfo, 
                            self.adminInfo, self.siteInfo, 
                            self.groupInfo)
        auditor = Auditor(self.siteInfo, self.groupInfo, 
                    self.adminInfo, self.userInfo)
        return (auditor, inviter)
