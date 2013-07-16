# -*- coding: utf-8 -*-
'''Create Users from CSV file.

This may appear to be a big scary module, but do not worry. Most of it
is devoted to writing the error message.'''
# import transaction
from zope.cachedescriptors.property import Lazy
from zope.formlib import form as formlib
from gs.group.base import GroupPage
from gs.profile.email.base.emailuser import EmailUser
from Products.GSProfile import interfaces as profileSchemas
from columns import Columns
from profilelist import ProfileList
from processor import CSVProcessor

import logging
log = logging.getLogger('GSCreateUsersFromCSV')


class CreateUsersInviteForm(GroupPage):
    # if this is set to true, we invite users. Otherwise we just add them.
    invite = True

    def __init__(self, group, request):
        super(CreateUsersInviteForm, self).__init__(group, request)

    @Lazy
    def acl_users(self):
        retval = self.context.site_root().acl_users
        return retval

    @Lazy
    def globalConfiguration(self):
        site_root = self.context.site_root()
        assert hasattr(site_root, 'GlobalConfiguration')
        retval = site_root.GlobalConfiguration
        return retval

    @property
    def invite_only(self):
        return self.invite

    @Lazy
    def profileSchemaName(self):
        site_root = self.context.site_root()
        assert hasattr(site_root, 'GlobalConfiguration')
        config = site_root.GlobalConfiguration
        ifName = config.getProperty('profileInterface', 'IGSCoreProfile')
        # --=mpj17=-- Sometimes profileInterface is set to ''
        ifName = (ifName and ifName) or 'IGSCoreProfile'
        retval = '%sAdminJoinCSV' % ifName
        assert hasattr(profileSchemas, ifName), \
            'Interface "%s" not found.' % ifName
        assert hasattr(profileSchemas, retval), \
            'Interface "%s" not found.' % retval
        return retval

    @property
    def profileSchema(self):
        return getattr(profileSchemas, self.profileSchemaName)

    @Lazy
    def profileFields(self):
        retval = formlib.Fields(self.profileSchema, render_context=False)
        return retval

    @Lazy
    def profileList(self):
        retval = ProfileList(self.context)
        return retval

    @Lazy
    def requiredColumns(self):
        retval = [p for p in self.profileList if p.value.required]
        return retval

    @property
    def columns(self):
        retval = []

        profileAttributes = {}
        for pa in self.profileList:
            profileAttributes[pa.token] = pa.title

        for i in range(0, len(self.profileList)):
            j = i + 65
            columnId = 'column%c' % chr(j)
            columnTitle = u'Column %c' % chr(j)
            column = {
              'columnId': columnId,
              'columnTitle': columnTitle,
              'profileList': self.profileList}
            retval.append(column)
        assert len(retval) > 0
        return retval

    @Lazy
    def adminInfo(self):
        retval = self.loggedInUserInfo
        return retval

    @Lazy
    def fromAddr(self):
        eu = EmailUser(self.context, self.adminInfo)
        addrs = eu.get_addresses()
        retval = addrs[0] if addrs else u''
        return retval

    @Lazy
    def subject(self):
        retval = u'Invitation to join {0}'.format(self.groupInfo.name)
        return retval

    @Lazy
    def message(self):
        m = u'''Hi there!

Please accept this invitation to join {0}. I have set everything up for
you, so you can start participating in the group as soon as you follow
the link below and accept this invitation.'''
        retval = m.format(self.groupInfo.name)
        return retval

    @property
    def preview_js(self):
        msg = self.message.replace(' ', '%20').replace('\n', '%0A')
        subj = self.subject.replace(' ', '%20')
        uri = u'admin_invitation_message_preview.html?form.body=%s&amp;'\
                'form.fromAddr=%s&amp;form.subject=%s' % \
                (msg, self.fromAddr, subj)
        js = u"window.open(%s, 'Message  Preview', "\
            "'height=360,width=730,menubar=no,status=no,tolbar=no')" % uri
        return js

    def process_form(self):
        form = self.context.REQUEST.form
        result = {}
        result['form'] = form

        if 'submitted' in form:
            result['message'] = u''
            result['error'] = False
            # FIXME: Fix logging
            #m = u'process_form: Adding users to %s (%s) on %s (%s) in'\
            #  u' bulk for %s (%s)' % \
            #  (self.groupInfo.name,   self.groupInfo.id,
            #   self.siteInfo.get_name(),    self.siteInfo.get_id(),
            #   self.adminInfo.name, self.adminInfo.id)
            #log.info(m)

            # Processing the CSV is done in three stages.
            #   1. Process the columns.
            columnProcessor = Columns(self.context, form)
            r = columnProcessor.process()
            result['message'] = u'\n'.join((result['message'], r['message']))
            result['error'] = result['error'] if result['error'] else r['error']
            columns = r['columns']
            processor = CSVProcessor(form, columns)
            #   2. Parse the file.
            if not result['error']:
                r = processor.process()
                m = u'{0}\n{1}'
                result['message'] = m.format(result['message'], r['message'])
                result['error'] = result['error'] or r['error']
                csvResults = r['csvResults']
            #   3. Interpret the data.
            if not result['error']:
                r = processor.process_csv_results(csvResults, form['delivery'])
                m = u'{0}\n{1}'
                result['message'] = m.format(result['message'], r['message'])
                result['error'] = result['error'] or r['error']

            assert 'error' in result
            assert type(result['error']) == bool
            assert 'message' in result
            assert type(result['message']) == unicode

        assert type(result) == dict
        assert 'form' in result
        assert type(result['form']) == dict
        return result


class CreateUsersAddForm(CreateUsersInviteForm):
    invite = False
