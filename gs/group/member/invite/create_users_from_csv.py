# coding=utf-8
'''Create Users from CSV file.

This may appear to be a big scary module, but do not worry. Most of it
is devoted to writing the error message.'''
from csv import DictReader
from zope.component import createObject
from zope.formlib import form
from zope.interface import implements, providedBy
from zope.app.apidoc.interface import getFieldsInOrder
from zope.schema import *
from zope.schema.vocabulary import SimpleTerm
from zope.schema.interfaces import ITokenizedTerm, IVocabulary,\
  IVocabularyTokenized, ITitledTokenizedTerm
from zope.interface.common.mapping import IEnumerableMapping 
from Products.Five import BrowserView
from Products.XWFCore.odict import ODict
from Products.CustomUserFolder.interfaces import IGSUserInfo
from Products.CustomUserFolder.userinfo import userInfo_to_anchor
from Products.GSGroupMember.groupmembership import *
from Products.GSProfile import interfaces as profileSchemas
from Products.GSProfile.utils import create_user_from_email, \
    enforce_schema
from Products.GSProfile.interfaceCoreProfile import deliveryVocab
from Products.GSProfile.emailaddress import NewEmailAddress, \
    NotAValidEmailAddress, DisposableEmailAddressNotAllowed, \
    EmailAddressExists
from audit import Auditor, INVITE_NEW_USER, INVITE_OLD_USER, \
    INVITE_EXISTING_MEMBER
from inviter import Inviter

import logging
log = logging.getLogger('GSCreateUsersFromCSV')

class CreateUsersForm(BrowserView):
    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)

        self.siteInfo = createObject('groupserver.SiteInfo', context)
        self.groupInfo = createObject('groupserver.GroupInfo', context)
        self.profileList = ProfileList(context)
        self.acl_users = context.site_root().acl_users
        site_root = context.site_root()
        assert hasattr(site_root, 'GlobalConfiguration')

        self.__admin = self.__subject = self.__message =  None
        self.__fromAddr = self.__profileInterfaceName = None
        self.__profileFields = None

    @property
    def profileSchemaName(self):
        if self.__profileInterfaceName == None:
            site_root = self.context.site_root()
            assert hasattr(site_root, 'GlobalConfiguration')
            config = site_root.GlobalConfiguration
            ifName = config.getProperty('profileInterface', 'IGSCoreProfile')
            # --=mpj17=-- Sometimes profileInterface is set to ''
            ifName = (ifName and ifName) or 'IGSCoreProfile'
            self.__profileInterfaceName = '%sAdminJoinCSV' % ifName
            assert hasattr(profileSchemas, ifName), \
                'Interface "%s" not found.' % ifName
            assert hasattr(profileSchemas, self.__profileInterfaceName), \
                'Interface "%s" not found.' % self.__profileInterfaceName
        return self.__profileInterfaceName

    @property
    def profileSchema(self):
        return getattr(profileSchemas, self.profileSchemaName)

    @property
    def profileFields(self):
        if self.__profileFields == None:
            self.__profileFields = form.Fields(self.profileSchema,
                                    render_context=False)
        return self.__profileFields
        
    @property
    def columns(self):
        retval = []
        
        profileAttributes = {}
        for pa in self.profileList:
            profileAttributes[pa.token] = pa.title
        
        for i in range(0, len(self.profileList)):
            j = i + 65
            columnId = 'column%c' % chr(j)
            columnTitle = u'Column %c'% chr(j)
            column = {
              'columnId':    columnId, 
              'columnTitle': columnTitle, 
              'profileList': self.profileList}
            retval.append(column)
        assert len(retval) > 0
        return retval

    @property
    def adminInfo(self):
        if self.__admin == None:
            self.__admin = createObject('groupserver.LoggedInUser', 
                                        self.context)
            assert user_admin_of_group(self.__admin, self.groupInfo)
        return self.__admin

    @property
    def fromAddr(self):
        if self.__fromAddr == None:
            self.__fromAddr = self.adminInfo.user.get_emailAddresses()[0]
        return self.__fromAddr
    @property
    def subject(self):
        if self.__subject == None:
            self.__subject = u'Invitation to join %s' % self.groupInfo.name
        return self.__subject
        
    @property
    def message(self):
        if self.__message == None:
            self.__message = u'''Hi there!

Please accept this invitation to join %s. I have set everything up for
you, so you can start participating in the group as soon as you follow
the link below and accept this invitation.''' % self.groupInfo.name
        return self.__message
        
    @property
    def preview_js(self):
        msg = self.message.replace(' ','%20').replace('\n','%0A')
        subj = self.subject.replace(' ', '%20')
        uri = 'admin_invitation_message_preview.html?form.body=%s&amp;'\
                'form.fromAddr=%s&amp;form.subject=%s' % \
                (msg, self.fromAddr, subj)
        js = "window.open(%s, 'Message  Preview', "\
            "'height=360,width=730,menubar=no,status=no,tolbar=no')" %\
            uri
        return js
    def process_form(self):
        form = self.context.REQUEST.form
        result = {}
        result['form'] = form

        if form.has_key('submitted'):
            result['message'] = u''
            result['error'] = False
            m = u'process_form: Adding users to %s (%s) on %s (%s) in'\
              u' bulk for %s (%s)' % \
              (self.groupInfo.name,   self.groupInfo.id,
               self.siteInfo.get_name(),    self.siteInfo.get_id(),
               self.adminInfo.name, self.adminInfo.id)
            log.info(m)
            
            # Processing the CSV is done in three stages.
            #   1. Process the columns.
            r = self.process_columns(form)
            result['message'] = '%s\n%s' % \
              (result['message'], r['message'])
            result['error'] = result['error'] or r['error']
            columns = r['columns']
            #   2. Parse the file.
            if not result['error']:
                r = self.process_csv_file(form, columns)
                result['message'] = '%s\n%s' %\
                  (result['message'], r['message'])
                result['error'] = result['error'] or r['error']
                csvResults = r['csvResults']
            #   3. Interpret the data.
            if not result['error']:
                r = self.process_csv_results(csvResults, form['delivery'])
                result['message'] = '%s\n%s' % \
                  (result['message'], r['message'])
                result['error'] = result['error'] or r['error']

            assert result.has_key('error')
            assert type(result['error']) == bool
            assert result.has_key('message')
            assert type(result['message']) == unicode

        assert type(result) == dict
        assert result.has_key('form')
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
        assert type(form) == dict
        assert 'csvfile' in form
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
            colPlural = len(notSpecified) > 1 and 'columns have' \
              or 'column has'
            colM = '\n'.join(['<li>%s</li>'% c.title for c in notSpecified])
            m = u'<p>The required %s not been specified:</p>\n<ul>%s</ul>' %\
              (colPlural, colM)
            message = u'%s\n%s' % (message, m)
            
        result = {'error':    error,
                  'message':  message,
                  'columns':  columns,
                  'form':   form}
        assert result.has_key('error')
        assert type(result['error']) == bool
        assert result.has_key('message')
        assert type(result['message']) == unicode
        assert result.has_key('columns')
        assert type(result['columns']) == list
        assert len(result['columns']) >= 2
        assert result.has_key('form')
        assert type(result['form']) == dict
        return result
    
    def get_unspecified_columns(self, columns):
        '''Get the unspecified required columns'''
        requiredColumns = [p for p in self.profileList if p.value.required]
        unspecified = []
        for requiredColumn in requiredColumns:
            if requiredColumn.token not in columns:
                unspecified.append(requiredColumn)
        return unspecified
    
    def process_csv_file(self, form, columns):
        '''Process the CSV file specified by the user.
        
        DESCRIPTION        
          Parse the CSV file that is supplied as part of the `form`. The
          parser turns each row into a dictionary, which has `columns`
          as the keys.
        
        ARGUMENTS
          form:     The form that contains the CSV file.
          columns:  The columns specification, as generated by
                    "process_columns".
          
        SIDE EFFECTS
          None.
          
        RETURNS
          A dictionary containing the following keys.
          
            Key         Type      Note
            ==========  ========  =======================================
            error       bool      True if an error was encounter.
            message     str       A feedback message.
            csvResults  instance  An instance of a DictReader    
            form        dict      The form that was passed as an argument.
        '''
        
        message = u''
        error = False
        if 'csvfile' in form:
            csvfile = form.get('csvfile')
            csvResults = DictReader(csvfile, columns)
        else:
            m = u'<p>There was no CSV file specified. Please specify a '\
              u'CSV file</p>'
            message = u'%s\n%s' % (message, m)
            error = True
            csvfile = None
            csvResults = None
        result = {'error':      error,
                  'message':    message,
                  'csvResults': csvResults,
                  'form':       form}
        assert result.has_key('error')
        assert type(result['error']) == bool
        assert result.has_key('message')
        assert type(result['message']) == unicode
        assert result.has_key('csvResults')
        assert isinstance(result['csvResults'], DictReader)
        assert result.has_key('form')
        assert type(result['form']) == dict
        return result

    def process_csv_results(self, csvResults, delivery):
        '''Process the CSV results, creating users and adding them to
           the group as necessary.
        
        ARGUMENTS
          csvResults: The CSV results, as generated by the
                      `process_csv_file` method.
          delivery:   The email delivery settings for the new group 
                      members.

        SIDE EFFECTS
          For each user in the CSV results, either
            * A new user is created if the user's email address is not
              registered with the system, or
            * The user is added to the site and group, if the user is not
              already a member.
          The side-effect is actually created by "process_row", which is
          called by this method.
          
        RETURNS
          A dictionary containing the following keys.
            error       bool      True if an error was encounter.
            message     str       A feedback message.
        '''
        assert isinstance(csvResults, DictReader)

        errorMessage = u'<ul>\n'
        errorCount = 0
        error = False
        newUserCount = 0
        newUserMessage = u'<ul>\n'
        existingUserCount = 0
        existingUserMessage  = u'<ul>\n'
        skippedUserCount = 0
        skippedUserMessage = u'<ul>\n'
        rowCount = 0
        csvResults.next() # Skip the first row (the header)
        # Map the data into the correctly named columns.
        for row in csvResults:
            try:
                r = self.process_row(row, delivery)
                error = error or r['error']
            
                if r['error']:
                    errorCount = errorCount + 1
                    errorMessage  = u'%s\n<li>%s</li>' %\
                      (errorMessage, r['message'])
                elif r['new'] == 1:
                    existingUserCount = existingUserCount + 1
                    existingUserMessage  = u'%s\n<li>%s</li>' %\
                      (existingUserMessage, r['message'])
                elif r['new'] == 2:
                    newUserCount = newUserCount + 1
                    newUserMessage  = u'%s\n<li>%s</li>' %\
                      (newUserMessage, r['message'])
                elif r['new'] == 3:
                    skippedUserCount = skippedUserCount + 1
                    skippedUserMessage  = u'%s\n<li>%s</li>' %\
                      (skippedUserMessage, r['message'])
                else:
                    assert False, 'Unexpected return value from process_row: %d'%\
                      r['new']
            except Exception, e:
                error = True
                errorCount = errorCount + 1
                errorMessage  = u'%s\n<li>'\
                  u'<strong>Unexpected Error:</strong> %s</li>' %\
                  (errorMessage, unicode(e))
            rowCount = rowCount + 1
        
        assert (existingUserCount + newUserCount + errorCount + \
          skippedUserCount) == rowCount,\
          'Discrepancy between counts: %d + %d + %d + %d != %d' %\
            (existingUserCount, newUserCount, errorCount, skippedUserCount,
             rowCount)
                     
        message = u'<p>%d rows were processed.</p>\n<ul>\n'%\
          (rowCount + 1)
        message = u'%s<li>The first row was treated as a header, and '\
          u'ignored.</li>\n' % message

        newUserMessage = u'%s</ul>\n' % newUserMessage
        if newUserCount > 0:
            wasWere = newUserCount == 1 and 'was' or 'were'
            userUsers = newUserCount == 1 and 'profile' or 'profiles'
            personPeople = newUserCount == 1 and 'person' or 'people'
            message = u'%s<li id="newUserInfo" class="disclosureWidget">'\
              u'<a href="#" class="disclosureButton"><strong>%d new '\
              u'%s</strong> %s created, and the %s %s invited to join %s.</a>\n'\
              u'<div class="disclosureShowHide" style="display:none;">'\
              u'%s</div></li>' % (message, newUserCount,  userUsers, 
                wasWere, personPeople, wasWere, self.groupInfo.name, newUserMessage)
        
        existingUserMessage = u'%s</ul>\n' % existingUserMessage
        if existingUserCount > 0:
            userUsers = existingUserCount == 1 and 'person' or 'people'
            wasWere = existingUserCount == 1 and 'was' or 'were'
            message = u'%s<li id="existingUserInfo"'\
              u'class="disclosureWidget">'\
              u'<a href="#" class="disclosureButton">%d %s that '\
              u'<strong>already had a profile</strong> %s invited to '\
              u'join to %s.</a>\n'\
              u'<div class="disclosureShowHide" style="display:none;">'\
              u'%s</div></li>' % (message, existingUserCount,  userUsers, 
                wasWere, self.groupInfo.name, existingUserMessage)
        
        skippedUserMessage = u'%s</ul>\n' % skippedUserMessage
        if skippedUserCount > 0:
            userUsers = skippedUserCount == 1 and 'member' or 'members'
            wasWere = skippedUserCount == 1 and 'was' or 'were'
            message = u'%s<li id="skippedUserInfo"'\
              u'class="disclosureWidget">'\
              u'<a href="#" class="disclosureButton"><strong>%d existing '\
              u'%s of %s %s skipped.</strong></a>\n'\
              u'<div class="disclosureShowHide" style="display:none;">'\
              u'%s</div></li>' % (message, skippedUserCount,  userUsers, 
                self.groupInfo.name, wasWere, skippedUserMessage)
        
        errorMessage = u'%s</ul>\n' % errorMessage
        if error:
            wasWere = errorCount == 1 and 'was' or 'were'
            errorErrors = errorCount == 1 and 'error' or 'errors'
            message = u'%s</ul><p>There %s %d %s:</p>\n' % \
              (message, wasWere, errorCount, errorErrors)
            message = u'%s%s\n' % (message, errorMessage)
            
        result = {'error':      error,
                  'message':    message}
        assert result.has_key('error')
        assert type(result['error']) == bool
        assert result.has_key('message')
        assert type(result['message']) == unicode
        return result

    def process_row(self, row, delivery):
        '''Process a row from the CSV file
        
        ARGUMENTS
          row        dict    The fields representing a row in the
                             CSV file. The column identifiers (alias
                             profile attribute identifiers) form
                             the keys.
          delivery   str     The message delivery settings for the new 
                             group members

        SIDE EFFECTS
            * A new user is created if the user's email address 
              "fields['email']" is not registered with the system, or
            * The user is added to the site and group, if the user is not
              already a member.
          
        RETURNS
          A dictionary containing the following keys.
            error       bool      True if an error was encounter.
            message     str       A feedback message.
            new         int       1 if an existing user was added to the
                                    group
                                  2 if a new user was created and added
                                  3 if the user was skipped as he or she
                                    is already a group member
                                  0 on error.
            user        instance  An instance of the CustomUser class.
        '''
        assert type(row) == dict
        assert 'toAddr' in row.keys()
        assert row['toAddr']
        
        user = None
        result = {}
        new = 0
        
        email = row['toAddr'].strip()
        
        emailChecker = NewEmailAddress(title=u'Email')
        emailChecker.context = self.context # --=mpj17=-- Legit?
        try:
            emailChecker.validate(email)
        except EmailAddressExists, e:
            user = self.acl_users.get_userByEmail(email)
            assert user, 'User for <%s> not found' % email
            userInfo = IGSUserInfo(user)
            auditor, inviter = self.get_auditor_inviter(userInfo)
            if user_member_of_group(user, self.groupInfo):
                new = 3
                auditor.info(INVITE_EXISTING_MEMBER, email)
                m = u'Skipped existing group member %s'% userInfo_to_anchor(userInfo)
            else:
                new = 1
                inviteId = inviter.create_invitation(row, False)
                auditor.info(INVITE_OLD_USER, email)
                inviter.send_notification(self.subject, self.message, 
                    inviteId, self.fromAddr, email)
                self.set_delivery_for_user(userInfo, delivery)
                m = u'%s has an existing profile' % userInfo_to_anchor(userInfo)
            error = False
        except DisposableEmailAddressNotAllowed, e:
            error = True
            m = self.error_msg(email, unicode(e))
        except NotAValidEmailAddress, e:
            error = True
            m = self.error_msg(email, unicode(e))
        else:
            userInfo = self.create_user(row)
            user = userInfo.user
            new = 2
            auditor, inviter = self.get_auditor_inviter(userInfo)
            inviteId = inviter.create_invitation(row, True)
            auditor.info(INVITE_NEW_USER, email)
            inviter.send_notification(self.subject, self.message, 
                inviteId, self.fromAddr, email)
            self.set_delivery_for_user(userInfo, delivery)
            error = False
            m = u'Created a profile for %s' % userInfo_to_anchor(userInfo)
            
        result = {'error':      error,
                  'message':    m,
                  'user':       user,
                  'new':        new}
        assert result
        assert type(result) == dict
        assert result.has_key('error')
        assert type(result['error']) == bool
        assert result.has_key('message')
        assert type(result['message']) == unicode
        assert result.has_key('user')
        # If an email address is invalid or disposable, user==None
        #assert isinstance(result['user'], CustomUser)
        assert result.has_key('new')
        assert type(result['new']) == int
        assert result['new'] in range(0, 5), '%d not in range'%result['new']
        return result
        
    def create_user(self, fields):
        assert type(fields) == dict
        assert 'toAddr' in fields
        assert fields['toAddr']
        
        email = fields['toAddr'].strip()
        
        user = create_user_from_email(self.context, email)
        userInfo = IGSUserInfo(user)
        enforce_schema(userInfo.user, self.profileSchema)
        changed = form.applyChanges(user, self.profileFields, fields)
        return userInfo
        
    def error_msg(self, email, msg):
        return\
          u'Did not create a profile for the email address '\
          u'<code class="email">%s</code>. %s' % (email, msg)

    def set_delivery_for_user(self, userInfo, delivery):
        '''Set the message delivery setting for the user

        ARGUMENTS
            userInfo    A UserInfo instance.
            delivery    The delivery settings as a string.
            
        SIDE EFFECTS
            Sets the delivery setting for the user in the group
            
        RETURNS
            None.
        '''
        assert not(userInfo.anonymous)
        assert delivery in deliveryVocab
        
        if delivery == 'email':
            # --=mpj17=-- The default is one email per post
            pass
        elif delivery == 'digest':
            userInfo.user.set_enableDigestByKey(self.groupInfo.id)
        elif delivery == 'web':
            userInfo.user.set_disableDeliveryByKey(self.groupInfo.id)

    def get_auditor_inviter(self, userInfo):
        inviter = Inviter(self.context, self.request, userInfo, 
                            self.adminInfo, self.siteInfo, 
                            self.groupInfo)
        auditor = Auditor(self.siteInfo, self.groupInfo, 
                    self.adminInfo, userInfo)
        return (auditor, inviter)

class ProfileList(object):
    implements(IVocabulary, IVocabularyTokenized)
    __used_for__ = IEnumerableMapping

    def __init__(self, context):
        self.context = context
        self.__properties = ODict()
        self.__profileInterfaceName = None

    @property
    def profileSchemaName(self):
        if self.__profileInterfaceName == None:
            site_root = self.context.site_root()
            assert hasattr(site_root, 'GlobalConfiguration')
            config = site_root.GlobalConfiguration
            ifName = config.getProperty('profileInterface', 'IGSCoreProfile')
            # --=mpj17=-- Sometimes profileInterface is set to ''
            ifName = (ifName and ifName) or 'IGSCoreProfile'
            self.__profileInterfaceName = '%sAdminJoinCSV' % ifName
            assert self.__profileInterfaceName != None
            assert hasattr(profileSchemas, ifName), \
                'Interface "%s" not found.' % ifName
            assert hasattr(profileSchemas, self.__profileInterfaceName), \
                'Interface "%s" not found.' % self.__profileInterfaceName
        return self.__profileInterfaceName

    @property
    def schema(self):
        return getattr(profileSchemas, self.profileSchemaName)

        
    def __iter__(self):
        """See zope.schema.interfaces.IIterableVocabulary"""
        retval = [SimpleTerm(self.properties[p], p, self.properties[p].title)
                  for p in self.properties.keys()]
        for term in retval:
              assert term
              assert ITitledTokenizedTerm in providedBy(term)
              assert term.value.title == term.title
        return iter(retval)

    def __len__(self):
        """See zope.schema.interfaces.IIterableVocabulary"""
        return len(self.properties)

    def __contains__(self, value):
        """See zope.schema.interfaces.IBaseVocabulary"""
        retval = False
        retval = value in self.properties
        assert type(retval) == bool
        return retval

    def getQuery(self):
        """See zope.schema.interfaces.IBaseVocabulary"""
        return None

    def getTerm(self, value):
        """See zope.schema.interfaces.IBaseVocabulary"""
        return self.getTermByToken(value)
        
    def getTermByToken(self, token):
        """See zope.schema.interfaces.IVocabularyTokenized"""
        for p in self.properties:
            if p == token:
                retval = SimpleTerm(self.properties[p], p, self.properties[p].title)
                assert retval
                assert ITitledTokenizedTerm in providedBy(retval)
                assert retval.token == retval.value
                return retval
        raise LookupError, token

    @property
    def properties(self):
        if len(self.__properties) == 0:
            assert self.context
            ifs = getFieldsInOrder(self.schema)
            for interface in ifs:
                self.__properties[interface[0]] = interface[1]
        retval = self.__properties
        assert isinstance(retval, ODict)
        assert retval
        return retval

