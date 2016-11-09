# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import os
import shutil
from tempfile import mkdtemp

from pythonic_testcase import *

from ddc.client.config import ALL_FIELD_NAMES
from ddc.storage.cdb.cdb_fixtures import create_cdb_with_dummy_data
from ddc.storage.cdb.cdb_check import open_cdb
from ddc.storage.locking import acquire_lock
from ddc.tool.cdb_tool import FormBatch


class CDBCheckTest(PythonicTestCase):
    def setUp(self):
        super(CDBCheckTest, self).setUp()
        self.env_dir = mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.env_dir)
        super(PythonicTestCase, self).tearDown()

    def test_can_return_cdb_instance(self):
        cdb_path = os.path.join(self.env_dir, 'foo.cdb')
        cdb_fp = create_cdb_with_dummy_data(nr_forms=1, filename=cdb_path)
        cdb_fp.close()

        result = open_cdb(cdb_path, field_names=ALL_FIELD_NAMES)
        assert_true(result)
        assert_not_none(result.cdb_fp)

        cdb = FormBatch(result.cdb_fp)
        assert_equals(1, cdb.count())
        cdb.close()

    def test_can_detect_locked_cdb_files(self):
        cdb_path = os.path.join(self.env_dir, 'foo.cdb')
        cdb_fp = create_cdb_with_dummy_data(nr_forms=1, filename=cdb_path)
        acquire_lock(cdb_fp, exclusive_lock=True, raise_on_error=True)

        result = open_cdb(cdb_path, field_names=ALL_FIELD_NAMES)
        assert_false(result)
        assert_none(result.cdb_fp)
        assert_contains('noch in Bearbeitung.', result.message)

        cdb_fp.close()

    def test_can_detect_cdb_files_with_trailing_junk(self):
        cdb_path = os.path.join(self.env_dir, 'foo.cdb')
        cdb_fp = create_cdb_with_dummy_data(nr_forms=1, filename=cdb_path)
        cdb_fp.seek(0, os.SEEK_END)
        cdb_fp.write(b'\x00' * 100)
        cdb_fp.close()

        result = open_cdb(cdb_path, field_names=ALL_FIELD_NAMES)
        assert_false(result)
        assert_none(result.cdb_fp)
        assert_contains(u'ungewöhnliche Größe', result.message)
