# coding=utf-8
import md5
from time import asctime
from Products.GSGroupMember.groupmembership import userInfo_to_user
from Products.XWFCore.XWFUtils import convert_int2b62

def set_digest(userInfo, groupInfo, data):
    delivery = 'delivery'
    email = 'email'
    digest = 'digest'
    web = 'web'
    assert data.has_key(delivery)
    assert data[delivery] in [email, digest, web]
    user = userInfo_to_user(userInfo)
    assert hasattr(user, 'set_enableDigestByKey')
    
    if data[delivery] == email:
        # --=mpj17=-- The default is one email per post
        pass
    elif data[delivery] == digest:
        user.set_enableDigestByKey(groupInfo.id)
    elif data[delivery] == web:
        user.set_disableDeliveryByKey(groupInfo.id)

def invite_id(siteId, groupId, userId, adminId, miscStr=''):
    print siteId
    print groupId
    print 'User ID %s' % userId
    print adminId
    print miscStr
    istr = asctime() + siteId + groupId + userId + adminId + miscStr
    print
    print istr
    print
    istr = asctime() + siteId + groupId + userId + adminId + miscStr
    inum = long(md5.new(istr).hexdigest(), 16)
    retval = str(convert_int2b62(inum))
    assert retval
    assert type(retval) == str
    return retval

