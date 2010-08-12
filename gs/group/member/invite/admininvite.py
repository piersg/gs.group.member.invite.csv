# coding=utf-8
from zope.component import createObject
from Products.GSContent.view import GSContentView
from Products.XWFCore.XWFUtils import get_the_actual_instance_from_zope

class AdminInviteView(GSContentView):
    def __init__(self, context, request):
        GSContentView.__init__(self, context, request)
        self.__groupInfo = None
        
    @property
    def groupInfo(self):
        if self.__groupInfo == None:
            self.__groupInfo = createObject('groupserver.GroupInfo', 
                                get_the_actual_instance_from_zope(self.context))
        assert self.__groupInfo
        return self.__groupInfo

