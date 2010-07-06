# coding=utf-8
from zope.schema import *
from zope.interface.interface import Interface
from zope.schema.vocabulary import SimpleVocabulary
from Products.GSProfile.interfaces import deliveryVocab

class IGSInvitationMessage(Interface):
    text = Bool(title=u'Text',
        description=u'Display the invitation as pure text, rather than '\
            u'a HTML pre-element. Call it command  coupling if you '\
            u'want, it is how the code works.',
        required=False,
        default=False)

    preview = Bool(title=u'Preview',
          description=u'True if the message is a preview.',
          required=False,
          default=False)

    toAddr = ASCIILine(title=u'To', 
        description=u'The email address of the person receiving the '\
            u'invitation.',
        required=False)

    fromAddr = ASCIILine(title=u'To', 
        description=u'The email address of the person sending the '\
            u'invitation.',
        required=False)

    supportAddr = ASCIILine(title=u'Support', 
        description=u'The email address of the support-group.',
        required=False)

    subject = TextLine(title=u'Subject',
        description=u'The subject-line of the invitation.',
        required=False)

    body = Text(title=u'Body',
        description=u'The body of the invitation.',
        required=True)
    
    invitationId = ASCIILine(title=u'Invitation Identifier',
        description=u'The identifier for the invitation to join the '\
            u'group',
        required=False,
        default='example')

class IGSInvitationMessageContentProvider(IGSInvitationMessage):
    pageTemplateFileName = ASCIILine(title=u"Page Template File Name",
          description=u'The name of the ZPT file that is used to '\
            u'render the status message.',
          required=False,
          default="browser/templates/invitationmessagecontentprovider.pt")

    message = Text(title=u'Invitation Message',
        description=u'The message that appears at the top of the email '\
            u'invitation to the new group member. The message will '\
            u'appear before the two links that allow the user to accept '\
            u'or reject the inviation.',
        required=True)
        
class IGSInvitationFields(Interface): 
    message = Text(title=u'Invitation Message',
        description=u'The message that appears at the top of the email '\
            u'invitation to the new group member. The message will '\
            u'appear before the link that allows the member to accept '\
            u'or reject the inviation.',
        required=True)

    fromAddr = Choice(title=u'Email From',
      description=u'The email address that you want in the "From" '\
        u'line in the invitation tat you send.',
      vocabulary = 'EmailAddressesForLoggedInUser',
      required=True)

    delivery = Choice(title=u'Group Message Delivery Settings',
      description=u'The message delivery settings for the new user',
      vocabulary=deliveryVocab,
      default='email')

    subject = TextLine(title=u'Subject',
        description=u'The subject line of the invitation message that '\
            u'will be sent to the new member',
        required=True)


class IGSInviteSiteMembers(IGSInvitationFields):
    site_members = List(title=u'Site Members',
      description=u'The members of this site that are not a member of '\
        u'this group.',
      value_type=Choice(title=u'Group',
                      vocabulary='groupserver.InviteMembersNonGroupMembers'),
      unique=True,
      required=True)

