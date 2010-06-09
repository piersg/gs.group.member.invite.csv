# coding=utf-8
'''Create Users from CSV file.
'''
from zope.component import createObject
from zope.interface import implements, providedBy
from zope.app.apidoc.interface import getFieldsInOrder
from zope.schema import *
from zope.schema.vocabulary import SimpleTerm
from zope.schema.interfaces import ITokenizedTerm, IVocabulary,\
  IVocabularyTokenized, ITitledTokenizedTerm
from zope.interface.common.mapping import IEnumerableMapping 
from Products.Five import BrowserView
from Products.XWFCore.odict import ODict
from Products.XWFCore.CSV import CSVFile
from Products.CustomUserFolder.CustomUser import CustomUser
from Products.CustomUserFolder.interfaces import IGSUserInfo
from Products.GSGroupMember.groupmembership import *
import interfaces, utils
from interfaceCoreProfile import deliveryVocab
from emailaddress import NewEmailAddress, NotAValidEmailAddress,\
  DisposableEmailAddressNotAllowed, EmailAddressExists
from zope.formlib import form

import logging
log = logging.getLogger('GSCreateUsersFromCSV')

class CreateUsersForm(BrowserView):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        
        self.siteInfo = createObject('groupserver.SiteInfo', context)
        self.groupInfo = createObject('groupserver.GroupInfo', context)
        self.profileList = ProfileList(context)
        self.acl_users = context.site_root().acl_users
        
        site_root = context.site_root()
        assert hasattr(site_root, 'GlobalConfiguration')
        config = site_root.GlobalConfiguration
        self.profileSchemaName = profileSchemaName = \
          config.getProperty('profileInterface', 'IGSCoreProfile')
        self.profileSchema = profileSchema = \
          getattr(interfaces, profileSchemaName)
        self.profileFields = form.Fields(self.profileSchema, render_context=False)
        
        self.__admin = None
        
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

    def get_admin(self):
        if self.__admin == None:
            self.__admin = createObject('groupserver.LoggedInUser', 
                                        self.context)
            assert user_admin_of_group(self.__admin, self.groupInfo)
        return self.__admin
        
    def process_form(self):
        form = self.context.REQUEST.form
        result = {}
        result['form'] = form

        if form.has_key('submitted'):
            result['message'] = u''
            result['error'] = False

            admin = self.get_admin()
            m = u'process_form: Adding users to %s (%s) on %s (%s) in'\
              u' bulk for %s (%s)' % \
              (self.groupInfo.name,   self.groupInfo.id,
               self.siteInfo.get_name(),    self.siteInfo.get_id(),
               self.__admin.name, self.__admin.id)
            log.info(m)
            
            r = self.process_columns(form)
            result['message'] = '%s\n%s' % \
              (result['message'], r['message'])
            result['error'] = result['error'] or r['error']
            columns = r['columns']

            if not result['error']:
                r = self.process_csv_file(form, columns)
                result['message'] = '%s\n%s' %\
                  (result['message'], r['message'])
                result['error'] = result['error'] or r['error']
                csvResults = r['csvResults']
                
            if not result['error']:
                r = self.process_csv_results(csvResults, columns, form['delivery'])
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
        
        ARGUMENTS
          form:     The form that contains the column specifications.

        SIDE EFFECTS
          None.
          
        RETURNS
          A dictionary containing the following keys.
            error     bool    True if an error was encounter.
            message   str     A feedback message.
            columns   dict    The columns the user specified. The 
                              dictionary keys are the column indices as
                              integers; the values are column IDs as 
                              strings.
            form      dict    The form that was passed as an argument.
        '''
        assert type(form) == dict
        assert 'csvfile' in form
        message = u''
        error = False
        
        columns = {}
        for key in form:
            if 'column' in key and form[key] != 'nothing':
                foo, col = key.split('column')
                i = ord(col) - 65
                columns[i] = form[key]
                
        requiredColumns = [p for p in self.profileList if p.value.required]
        notSpecified = []

        providedColumns = columns.values()
        for requiredColumn in requiredColumns:
            if requiredColumn.token not in providedColumns:
                notSpecified.append(requiredColumn)
        if notSpecified:
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
        assert type(result['columns']) == dict
        assert len(result['columns']) >= 2
        assert result.has_key('form')
        assert type(result['form']) == dict
        return result

    def process_csv_file(self, form, columns):
        '''Process the CSV file specified by the user.
        
        ARGUMENTS
          form:     The form that contains the CSV file.
          columns:  The columns specification, as generated by
                    "process_columns".
          
        SIDE EFFECTS
          None.
          
        RETURNS
          A dictionary containing the following keys.
            error       bool      True if an error was encounter.
            message     str       A feedback message.
            csvResults  instance  An instance of a CSVFile    
            form        dict      The form that was passed as an argument.
        '''
        
        message = u''
        error = False
        if 'csvfile' not in form:
            m = u'<p>There was no CSV file specified. Please specify a '\
              u'CSV file</p>'
            message = u'%s\n%s' % (message, m)
            error = True
            csvfile = None
            csvResults = None
        else:
            csvfile = form.get('csvfile')
            try:
                csvResults = CSVFile(csvfile, [str]*len(columns))
            except AssertionError, x:
                m = u'<p>The number of columns you have defined (%s) '\
                  u'does not match the number of columns in the CSV file '\
                  u'you provided.</p>' % len(columns)
                error = True
                message = u'%s\n%s' % (message, m)
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
        # assert isinstance(result['csvResults'], CSVFile)
        assert result.has_key('form')
        assert type(result['form']) == dict
        return result

    def process_csv_results(self, csvResults, columns, delivery):
        '''Process the CSV results, creating users and adding them to
           the group as necessary.
        
        ARGUMENTS
          csvResults: The CSV results, as generated by
                      "process_csv_file"
          columns:    The columns specification, as generated by
                      "process_columns".
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
        assert isinstance(csvResults, CSVFile)
        assert type(columns) == dict        

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
        
        # Map the data into the correctly named columns.
        for row in csvResults.mainData:
            try:
                fieldmap = {}
                for column in columns:
                    fieldmap[columns[column]] = row[column]
                r = self.process_row(fieldmap, delivery)
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
        assert rowCount == len(csvResults.mainData),\
          'Row count != length of CSV main data: %s != %s' %\
            (rowCount, len(csvResults.mainData))
        
        message = u'<p>%d rows were processed.</p>\n<ul>\n'%\
          (rowCount + 1)
        message = u'%s<li>The first row was treated as a header, and '\
          u'ignored.</li>\n' % message

        newUserMessage = u'%s</ul>\n' % newUserMessage
        if newUserCount > 0:
            wasWere = newUserCount == 1 and 'was' or 'were'
            userUsers = newUserCount == 1 and 'user' or 'users'
            message = u'%s<li id="newUserInfo" class="disclosureWidget">'\
              u'<a href="#" class="disclosureButton"><strong>%d new '\
              u'%s</strong> %s created, and added to %s.</a>\n'\
              u'<div class="disclosureShowHide" style="display:none;">'\
              u'%s</div></li>' % (message, newUserCount,  userUsers, 
                wasWere, self.groupInfo.get_name(), newUserMessage)
        
        existingUserMessage = u'%s</ul>\n' % existingUserMessage
        if existingUserCount > 0:
            userUsers = existingUserCount == 1 and 'user' or 'users'
            wasWere = existingUserCount == 1 and 'was' or 'were'
            message = u'%s<li id="existingUserInfo"'\
              u'class="disclosureWidget">'\
              u'<a href="#" class="disclosureButton"><strong>%d existing '\
              u'%s</strong> %s invited to join to %s.</a>\n'\
              u'<div class="disclosureShowHide" style="display:none;">'\
              u'%s</div></li>' % (message, existingUserCount,  userUsers, 
                wasWere, self.groupInfo.get_name(), existingUserMessage)
        
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
                self.groupInfo.get_name(), wasWere, skippedUserMessage)
        
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

    def process_row(self, fields, delivery):
        '''Process a row from the CSV file
        
        ARGUMENTS
          fields     dict    The fields representing a row in the CSV file.
                             The column identifiers (alias profile 
                             attribute identifiers) form the keys.
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
        assert type(fields) == dict
        assert 'email' in fields
        assert fields['email']
        
        user = None
        result = {}
        new = 0
        
        email = fields['email'].strip()
        
        emailChecker = NewEmailAddress(title=u'Email')
        emailChecker.context = self.context # --=mpj17=-- Legit?
        try:
            emailChecker.validate(email)
        except EmailAddressExists, e:
            new = 1 # Possibly changed to 3 later
            user = self.acl_users.get_userByEmail(email)
            assert user, 'User for <%s> not found' % email
            userInfo = IGSUserInfo(user)

            if user_member_of_group(user, self.groupInfo):
                new = 3
                m = u'Skipped adding %s (%s) to the group %s (%s) as the '\
                  u'user is already a member' % \
                  (userInfo.name, user.id, 
                   self.groupInfo.name, self.groupInfo.id)
                log.info(m)
                m = u'Skipped existing group member '\
                  u'<a class="fn" href="%s">%s</a>' %\
                  (userInfo.url, userInfo.name)
            else:
                m = u'Invited existing user <a class="fn" href="%s">%s</a>' %\
                (userInfo.url, userInfo.name)
                invite_to_groups(userInfo, self.get_admin(), self.groupInfo)
                self.set_delivery_for_user(userInfo, delivery)
            error = False
        except DisposableEmailAddressNotAllowed, e:
            error = True
            m = self.error_msg(email, unicode(e))
        except NotAValidEmailAddress, e:
            error = True
            m = self.error_msg(email, unicode(e))
        else:
            userInfo = self.create_user(fields)
            user = userInfo.user
            new = 2
            join_group(user, self.groupInfo)
            self.set_delivery_for_user(userInfo, delivery)
            error = False
            m = u'Created new user <a class="fn" href="%s">%s</a>' %\
              (userInfo.url, userInfo.name)
            
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
        assert 'email' in fields
        assert fields['email']
        
        email = fields['email'].strip()
        
        user = utils.create_user_from_email(self.context, email)
        userInfo = IGSUserInfo(user)
        # Add profile attributes 
        utils.enforce_schema(user, self.profileSchema)
        changed = form.applyChanges(user, self.profileFields, fields)
        utils.send_add_user_notification(user, self.get_admin(),
          self.groupInfo, u'')
        return userInfo

    def error_msg(self, email, msg):
        return\
          u'Did not create a user for the email address '\
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

class ProfileList(object):
    implements(IVocabulary, IVocabularyTokenized)
    __used_for__ = IEnumerableMapping

    def __init__(self, context):
        self.context = context
        self.__properties = ODict()

        site_root = context.site_root()

        assert hasattr(site_root, 'GlobalConfiguration')
        config = site_root.GlobalConfiguration
        
        profileSchemaName = config.getProperty('profileInterface',
                                              'IGSCoreProfile')
        profileSchemaName = '%sAdminJoinCSV' % profileSchemaName
        assert hasattr(interfaces, profileSchemaName), \
            'Interface "%s" not found.' % profileSchemaName
        self.__schema = getattr(interfaces, profileSchemaName)
        
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
        assert self.context
        if len(self.__properties) == 0:
            ifs = getFieldsInOrder(self.__schema)
            for interface in ifs:
                self.__properties[interface[0]] = interface[1]
        retval = self.__properties
        assert isinstance(retval, ODict)
        assert retval
        return retval

