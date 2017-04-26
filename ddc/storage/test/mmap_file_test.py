# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import io
import os
import tempfile

from ddt import ddt as DataDrivenTestCase, data
from pythonic_testcase import *
import six

from ddc.storage.mmap_file import MMapFile


@DataDrivenTestCase
class MMapFileTest(PythonicTestCase):
    def setUp(self):
        self.temp_fname = tempfile.mktemp()
        testfile = io.open(self.temp_fname, 'wb')
        testfile.write(b'hallo')
        testfile.close()

    def tearDown(self):
        os.unlink(self.temp_fname)

    @data('write', 'copy')
    def test_interface(self, access):
        mm = MMapFile(self.temp_fname, 'write')
        assert_equals(b'hallo', mm[:])
        mm.flush()
        if six.PY3:
            mm[3] = ord(b'X')
        else:
            mm[3] = b'X'
        mm[4:5] = mm[:1]
        mm.close()
        assert_true(mm.closed)
        with assert_raises(ValueError):
            mm[0] = 0
        assert_equals('halXh', open(self.temp_fname).read())
