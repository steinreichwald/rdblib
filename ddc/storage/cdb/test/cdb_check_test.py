# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import os

from pythonic_testcase import *

from ddc.storage.testhelpers import use_tempdir
from ddc.storage.cdb.cdb_fixtures import create_cdb_with_dummy_data
from ddc.storage.cdb.cdb_check import open_cdb
from ddc.storage.locking import acquire_lock
from ddc.tool.cdb_tool import FormBatch


class CDBCheckTest(PythonicTestCase):
    def test_can_return_cdb_instance(self):
        with use_tempdir() as env_dir:
            cdb_path = os.path.join(env_dir, 'foo.cdb')
            cdb_fp = create_cdb_with_dummy_data(nr_forms=1, filename=cdb_path)
            cdb_fp.close()

            result = open_cdb(cdb_path)
            assert_true(result)
            assert_not_none(result.cdb_fp)

            cdb = FormBatch(result.cdb_fp)
            assert_equals(1, cdb.count())

    def test_can_detect_locked_cdb_files(self):
        with use_tempdir() as env_dir:
            cdb_path = os.path.join(env_dir, 'foo.cdb')
            cdb_fp = create_cdb_with_dummy_data(nr_forms=1, filename=cdb_path)
            acquire_lock(cdb_fp, exclusive_lock=True, raise_on_error=True)

            result = open_cdb(cdb_path)
            assert_false(result)
            assert_none(result.cdb_fp)
            assert_contains('noch in Bearbeitung.', result.message)

            cdb_fp.close()
