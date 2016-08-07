# -*- coding: utf-8 -*-
############################################################################
#
# Copyright © 2013, 2014 OnlineGroups.net and Contributors.
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
from json import dumps as to_json
from chardet import detect
from zope.cachedescriptors.property import Lazy
from zope.contenttype import guess_content_type
from zope.formlib import form as formlib
from gs.content.form.api.json import SiteEndpoint
from gs.content.form.base import multi_check_box_widget
from .interface import ICsv
from .unicodereader import UnicodeDictReader
from csv import Sniffer, excel


class CSV2JSON(SiteEndpoint):
    label = 'POST CSV data to this URL to parse it, and transform it ' \
            'into a JSON object.'

    def __init__(self, site, request):
        super(CSV2JSON, self).__init__(site, request)

    @Lazy
    def form_fields(self):
        retval = formlib.Fields(ICsv, render_context=False)
        retval['columns'].custom_widget = multi_check_box_widget
        assert retval
        return retval

    @staticmethod
    def guess_encoding(byteString):
        d = detect(byteString)
        retval = d['encoding'] if d['encoding'] else 'utf-8'
        return retval

    @formlib.action(label='Submit', prefix='', failure='process_failure')
    def process_success(self, action, data):
        return self.actual_process(data)

    def actual_process(self, data):
        cols = data['columns']
        csv = BytesIO(data['csv'])  # The file is Bytes, encoded.
        encoding = self.guess_encoding(data['csv'])
        # TODO: Delivery?

        try:
            dialect = Sniffer().sniff(csv.readline(), [',', '\t'])
        except err:
            dialect = excel
        csv.seek(0)
        reader = UnicodeDictReader(csv, cols, encoding=encoding, dialect=dialect)
        profiles = []
        retval = None
        try:
            next(reader)  # Skip the first row (the header)
        except UnicodeDecodeError as e:
            t = guess_content_type(body=data['csv'])[0]
            msg = 'The file is different from what is required. (It '\
                  'appears to be a {0} file.) Please check that  you '\
                  'selected the correct CSV file.'
            m = {'status': -2,
                 'message': [msg.format(t.split('/')[0]), str(e), t]}
            retval = to_json(m)
        except StopIteration:
            msg = 'The file appears to be empty. Please check that you '\
                  'generated the CSV file correctly.'
            m = {'status': -5, 'message': [msg, 'no-rows']}
            retval = to_json(m)
        else:
            rowCount = 0
            for row in reader:
                rowCount += 1
                if len(row) != len(cols):
                    # *Technically* the number of columns in CSV rows can be
                    # arbitary. However, I am enforcing a strict
                    # interpretation for sanity's sake.
                    msg = 'Row {0} had {1} columns, rather than {2}. ' \
                          'Please check the file.'
                    # Name hack.
                    m = {'status': -3,
                         'message': [msg.format(rowCount, len(row),
                                     len(cols))]}
                    retval = to_json(m)
                    profiles = []
                    # --=mpj17=-- I think this is the first time I have used
                    # break in actual code. Wow.
                    break
                profiles.append(row)
        if profiles and (not retval):
            retval = to_json(profiles)
        elif (not profiles) and not(retval):
            msg = 'No rows were found in the CSV file. '\
                  'Please check that  you selected the correct CSV file.'
            m = {'status': -4,
                 'message': [msg, 'no-rows']}
            retval = to_json(m)
        assert retval, 'No retval'
        return retval

    def process_failure(self, action, data, errors):
        retval = self.build_error_response(action, data, errors)
        return retval
