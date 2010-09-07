# coding=utf-8
from zope.component import createObject, provideAdapter, adapts
from zope.pagetemplate.pagetemplatefile import PageTemplateFile
from zope.contentprovider.interfaces import UpdateNotCalled
from zope.interface import Interface, implements
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from interfaces import IGSInvitationMessageContentProvider

class InvitationMessageContentProvider(object):
    """Invitation Message content, in both HTML and TXT formats.
    """

    implements( IGSInvitationMessageContentProvider )
    adapts(Interface,
        IDefaultBrowserLayer,
        Interface)

    def __init__(self, context, request, view):
        self.__parent__ = self.view = view
        self.__updated = False

        self.context = context
        self.request = request
        
    def update(self):
        self.__updated = True

        self.siteInfo = createObject('groupserver.SiteInfo', 
          self.context)
        self.groupInfo = createObject('groupserver.GroupInfo', 
          self.context)
        self.userInfo = createObject('groupserver.LoggedInUser', 
          self.context)

    def render(self):
        if not self.__updated:
            raise UpdateNotCalled

        pageTemplate = PageTemplateFile(self.pageTemplateFileName)
        return pageTemplate(view=self)
        
    #########################################
    # Non standard methods below this point #
    #########################################

