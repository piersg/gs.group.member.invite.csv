# -*- coding: utf-8 -*-
# <http://docs.python.org/2.7/library/csv.html#csv.DictReader>
from codecs import getreader
from csv import DictReader, excel
from gs.core import to_unicode_or_bust


class UTF8Recoder(object):
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeDictReader(object):
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, cols, dialect=excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = DictReader(f, cols, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        retval = dict([(to_unicode_or_bust(k), to_unicode_or_bust(v))
                       for k, v in row.items()])
        return retval

    def __iter__(self):
        return self
