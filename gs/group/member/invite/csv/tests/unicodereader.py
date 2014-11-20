# -*- coding: utf-8 -*-
############################################################################
#
# Copyright © 2014 OnlineGroups.net and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
############################################################################
from __future__ import absolute_import, unicode_literals
from io import BytesIO
from unittest import TestCase
from gs.group.member.invite.csv.unicodereader import UnicodeDictReader


class TestUnicodeReader(TestCase):
    'Test the UnicodeDictReader'

    def assert_name_email(self, name, email, item):
        m = 'Name does not match: {0} != {1}'.format(name, item['name'])
        self.assertEqual(name, item['name'], m)
        m = 'Email does not match: {0} != {1}'.format(email, item['email'])
        self.assertEqual(email, item['email'], m)

    def test_ascii(self):
        csv = BytesIO(b'''"Michael JasonSmith",mpj17@onlinegroups.net
Member,member@example.com''')

        u = UnicodeDictReader(csv, ['name', 'email'], encoding='ascii')

        l = list(u)
        self.assertEqual(2, len(l))
        self.assert_name_email('Michael JasonSmith',
                               'mpj17@onlinegroups.net', l[0])
        self.assert_name_email('Member',
                               'member@example.com', l[1])

    def test_latin1(self):
        csv = BytesIO(b'''"Michael JasonSmith",mpj17@onlinegroups.net
M\xe9mb\xe9r,member@example.com''')

        u = UnicodeDictReader(csv, ['name', 'email'], encoding='latin-1')

        l = list(u)
        self.assertEqual(2, len(l))
        self.assert_name_email('Michael JasonSmith',
                               'mpj17@onlinegroups.net', l[0])
        self.assert_name_email('Mémbér',
                               'member@example.com', l[1])

    def test_utf8(self):
        csv = BytesIO(b'''"Michael JasonSmith",mpj17@onlinegroups.net
M\xc3\xa9mb\xc3\xa9r \xf0\x9f\x98\x84,member@example.com''')

        u = UnicodeDictReader(csv, ['name', 'email'], encoding='utf-8')

        l = list(u)
        self.assertEqual(2, len(l))
        self.assert_name_email('Michael JasonSmith',
                               'mpj17@onlinegroups.net', l[0])
        self.assert_name_email('Mémbér \U0001f604',
                               'member@example.com', l[1])
