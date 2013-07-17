# -*- coding: utf-8 -*-
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

# TODO:  Refactor this product. The CSV processor should sort the goats from
#        the sheep (or the members, non members, new people, and errors from
#        each other). Seperate inviters should issue invites to the appropriate
#        members.


class CreateUsersInviteForm(GroupPage):
    # if this is set to true, we invite users. Otherwise we just add them.
    invite = True

    def __init__(self, group, request):
        super(CreateUsersInviteForm, self).__init__(group, request)

    @Lazy
    def globalConfiguration(self):
        site_root = self.context.site_root()
        assert hasattr(site_root, 'GlobalConfiguration'), \
            'No GlobalConfiguration'
        retval = site_root.GlobalConfiguration
        return retval

    @property
    def invite_only(self):
        return self.invite

    @Lazy
    def profileSchemaName(self):
        ifName = self.globalConfiguration.getProperty('profileInterface',
                                                        'IGSCoreProfile')
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
            processor = CSVProcessor(self.context, self.request, form, columns,
                                        self.subject, self.message,
                                        self.fromAddr, self.profileSchema,
                                        self.profileFields)
            #   2. Parse the file.
            if not result['error']:
                r = processor.process()
                result['message'] = u'\n'.join((result['message'],
                                                r['message']))
                result['error'] = result['error'] or r['error']
                csvResults = r['csvResults']
            #   3. Interpret the data.
            if not result['error']:
                try:
                    r = processor.process_csv_results(csvResults,
                                                        form['delivery'])
                except UnicodeDecodeError, ude:
                    result['error'] = True
                    m = u'<p>Error reading the CSV file (did you select the '\
                        u'correct file?): <span class="muted">{0}</p></p>'
                    result['message'] = m.format(ude)
                else:
                    m = u'\n'.join((result['message'], r['message']))
                    result['message'] = m
                    result['error'] = result['error'] or r['error']

            assert 'error' in result
            assert type(result['error']) == bool
            assert 'message' in result
            assert type(result['message']) == unicode

        assert type(result) == dict
        assert 'form' in result
        assert type(result['form']) == dict

        contentType = 'text/html; charset=UTF-8'
        self.request.response.setHeader('Content-Type', contentType)
        return result


class CreateUsersAddForm(CreateUsersInviteForm):
    invite = False
