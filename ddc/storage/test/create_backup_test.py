# -*- coding: utf-8 -*-

import hashlib
import os

from pythonic_testcase import *

from ddc.lib.fake_fs_utils import FakeFS
from ..utils import create_backup


def md5sum_for_file(path):
    with open(path, 'rb') as fp:
        md5 = hashlib.md5()
        md5.update(fp.read())
        return md5.hexdigest()


class CreateBackupTest(PythonicTestCase):
    def setUp(self):
        super().setUp()
        self.fs = FakeFS.set_up(test=self)

    def test_can_create_backup(self):
        source_path = self._create_file('/data/foo.bin', b'some data')
        md5_source = md5sum_for_file(source_path)
        backup_dir = '/backup'
        assert_false(os.path.exists(backup_dir))
        backup_path = create_backup(source_path, backup_dir)

        assert_not_equals(source_path, backup_path)
        assert_true(os.path.exists(backup_path))
        assert_true(backup_path.startswith(backup_dir))
        md5_backup = md5sum_for_file(backup_path)
        assert_equals(md5_source, md5_backup)

    # --- internal helpers ----------------------------------------------------
    def _create_file(self, file_path, content):
        dirname = os.path.dirname(file_path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(file_path, 'wb') as fp:
            fp.write(content)
        return file_path
