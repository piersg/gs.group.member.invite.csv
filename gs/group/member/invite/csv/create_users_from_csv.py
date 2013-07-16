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
from profilelist import ProfileList

import logging
log = logging.getLogger('GSCreateUsersFromCSV')


class CreateUsersInviteForm(GroupPage):
    # if this is set to true, we invite users. Otherwise we just add them.
    invite = True

    def __init__(self, group, request):
        super(CreateUsersInviteForm, self).__init__(group, request)

    @Lazy
    def profileList(self):
        retval = ProfileList(self.context)
        return retval

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
            r = self.process_columns(form)
            result['message'] = u'%s\n%s' % (result['message'], r['message'])
            result['error'] = result['error'] if result['error'] else r['error']
            columns = r['columns']
            #   2. Parse the file.
            if not result['error']:
                r = self.process_csv_file(form, columns)
                m = u'{0}\n{1}'
                result['message'] = m.format(result['message'], r['message'])
                result['error'] = result['error'] or r['error']
                csvResults = r['csvResults']
            #   3. Interpret the data.
            if not result['error']:
                r = self.process_csv_results(csvResults, form['delivery'])
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

    def process_columns(self, form):
        '''Process the columns specified by the user.

        DESCRIPTION
          The administrator can create a CSV with the columns in any
          order that he or she likes. However, the admin must specify
          the columns seperately so we know what is entered. The job
          of this method is to parse the column spec.

        ARGUMENTS
          form:     The form that contains the column specifications.

        SIDE EFFECTS
          None.

        RETURNS
          A dictionary containing the following keys.
            error     bool    True if an error was encounter.
            message   str     A feedback message.
            columns   list    The columns the user specified. The list
                              values are column IDs as strings.
            form      dict    The form that was passed as an argument.
        '''
        assert type(form) == dict, 'The form is not a dict'
        assert 'csvfile' in form, 'There is no "csvfile" in the form'
        message = u''
        error = False

        colDict = {}
        for key in form:
            if 'column' in key and form[key] != 'nothing':
                foo, col = key.split('column')
                i = ord(col) - 65
                colDict[i] = form[key]
        columns = [colDict[i] for i in range(0, len(colDict))]

        unspecified = self.get_unspecified_columns(columns)
        if unspecified:
            error = True
            colPlural = len(unspecified) > 1 and 'columns have' \
              or 'column has'
            colM = '\n'.join(['<li>%s</li>' % c.title for c in unspecified])
            m = u'<p>The required %s not been specified:</p>\n<ul>%s</ul>' %\
              (colPlural, colM)
            message = u'%s\n%s' % (message, m)

        result = {'error': error,
                  'message': message,
                  'columns': columns,
                  'form': form}
        assert 'error' in result
        assert type(result['error']) == bool
        assert 'message' in result
        assert type(result['message']) == unicode
        assert 'columns' in result
        assert type(result['columns']) == list
        assert len(result['columns']) >= 2
        assert 'form' in result
        assert type(result['form']) == dict
        return result

    @Lazy
    def requiredColumns(self):
        retval = [p for p in self.profileList if p.value.required]
        return retval

    def get_unspecified_columns(self, columns):
        '''Get the unspecified required columns'''
        unspecified = []
        for requiredColumn in self.requiredColumns:
            if requiredColumn.token not in columns:
                unspecified.append(requiredColumn)
        return unspecified


class CreateUsersAddForm(CreateUsersInviteForm):
    invite = False
