# coding=utf-8
import pytz
from datetime import  datetime
import sqlalchemy as sa

class InvitationQuery(object):
    def __init__(self, da):
        self.userInvitationTable = da.createTable('user_group_member_invitation')

    def add_invitation(self, invitiationId, siteId, groupId, userId, 
                       invtUsrId, initialInvite = False):
        assert invitiationId, 'invitiationId is %s' % invitiationId
        assert siteId, 'siteId is %s' % siteId
        assert groupId, 'groupId is %s' % groupId
        assert userId, 'userId is %s' % userId
        assert invtUsrId, 'invtUsrId is %s' % invtUsrId
        
        d = datetime.utcnow().replace(tzinfo=pytz.utc)
        i = self.userInvitationTable.insert()
        i.execute(invitation_id = invitiationId,
          site_id = siteId,
          group_id = groupId,
          user_id = userId,
          inviting_user_id = invtUsrId,
          invitation_date = d,
          initial_invite = initialInvite)

