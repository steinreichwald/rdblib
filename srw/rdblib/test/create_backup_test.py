# -*- coding: utf-8 -*-

import hashlib
import os

from pythonic_testcase import *

from ..lib.fake_fs_utils import FakeFS
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

    def test_can_handle_non_existing_source(self):
        bad_path = '/invalid/test.rdb'
        backup_dir = '/backup'
        assert_false(os.path.exists(bad_path))
        assert_false(os.path.exists(backup_dir))

        with assert_raises(FileNotFoundError):
            create_backup(bad_path, backup_dir)
        assert_false(os.path.exists(backup_dir))

        backup_path = create_backup(bad_path, backup_dir, ignore_errors=True)
        assert_false(os.path.exists(backup_dir))
        assert_none(backup_path)

    def test_can_handle_source_with_insufficient_privileges(self):
        source_path = self._create_file('/data/foo.bin', b'some data')
        os.chmod(source_path, 0)
        self._assert_not_readable(source_path)
        backup_dir = '/backup'
        assert_false(os.path.exists(backup_dir))

        with assert_raises(PermissionError):
            create_backup(source_path, backup_dir)
        assert_false(os.path.exists(backup_dir))

        backup_path = create_backup(source_path, backup_dir, ignore_errors=True)
        assert_false(os.path.exists(backup_dir))
        assert_none(backup_path)

    def test_can_handle_inability_create_backup_directory(self):
        source_path = self._create_file('/data/foo.bin', b'some data')
        foo_dir = '/foo'
        os.makedirs(foo_dir, mode=0)
        self._assert_directory_not_accessible(foo_dir)
        backup_dir = os.path.join(foo_dir, 'backup')
        assert_false(os.path.exists(backup_dir))

        with assert_raises(Exception):
            create_backup(source_path, backup_dir)

        backup_path = create_backup(source_path, backup_dir, ignore_errors=True)
        assert_none(backup_path)

    def test_can_handle_backup_directory_without_permission_to_create_files(self):
        source_path = self._create_file('/data/foo.bin', b'some data')
        backup_dir = '/backup'
        os.makedirs(backup_dir, mode=0)
        self._assert_directory_not_accessible(backup_dir)

        with assert_raises(PermissionError):
            create_backup(source_path, backup_dir)

        backup_path = create_backup(source_path, backup_dir, ignore_errors=True)
        assert_none(backup_path)


    # --- internal helpers ----------------------------------------------------
    def _assert_not_readable(self, file_path):
        with assert_raises(PermissionError, message='expected insufficient permissions to open %s' % file_path):
            open(file_path, 'r')

    def _assert_directory_not_accessible(self, dir_path):
        dummy_path = os.path.join(dir_path, 'dummy.txt')
        with assert_raises(PermissionError, message='was able to create file %s' % dummy_path):
            open(dummy_path, 'wb')

    # --- internal helpers ----------------------------------------------------
    def _create_file(self, file_path, content):
        dirname = os.path.dirname(file_path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(file_path, 'wb') as fp:
            fp.write(content)
        return file_path
