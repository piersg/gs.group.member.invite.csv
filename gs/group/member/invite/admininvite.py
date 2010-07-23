# coding=utf-8
from zope.component import createObject
from Products.GSContent.view import GSContentView

class AdminInviteView(GSContentView):
    def __init__(self, context, request):
        GSContentView.__init__(self, context, request)
        self.__groupInfo = None
        
    @property
    def groupInfo(self):
        if self.__groupInfo == None:
            self.__groupInfo = createObject('groupserver.GroupInfo', 
                                self.context.aq_self)
        assert self.__groupInfo
        return self.__groupInfo

