# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import os
import subprocess
import sys
import tempfile
import time

from pythonic_testcase import *

from ddc.storage.locking import acquire_lock, unlock
from ddc.platf.platform_quirks import is_windows


def unlink_with_retry(filename, tries=10):
    i = 0
    while os.path.exists(filename) and i < tries:
        try:
            os.unlink(filename)
        except PermissionError:
            i += 1
            time.sleep(0.1)
            continue
        break
    if i == tries:
        sys.stderr.write('Unable to clear temporary file %r.' % filename)


class LockingTest(PythonicTestCase):

    def setUp(self):
        self.tempfp = None

    def tearDown(self):
        if self.tempfp is not None:
            filename = self.tempfp.name
            self.tempfp.close()
            unlink_with_retry(filename)

    def test_can_lock_and_unlock_files(self):
        self.tempfp = tempfile.NamedTemporaryFile(mode='w', delete=False)
        self.tempfp.close()
        temp_name = self.tempfp.name
        self.assert_is_unlocked(temp_name)

        fp = open(temp_name)
        acquire_lock(fp)
        self.assert_is_locked(fp.name)
        unlock(fp)
        if is_windows():
            # Windows does not allow opening the file twice so we need to close
            # it first.
            fp.close()
        self.assert_is_unlocked(temp_name)

    def test_can_acquire_shared_lock(self):
        self.tempfp = tempfile.NamedTemporaryFile(mode='w', delete=False)
        self.tempfp.close()
        temp_name = self.tempfp.name
        self.assert_is_unlocked(temp_name)

        fp = open(temp_name)
        acquire_lock(fp, exclusive_lock=False)
        self.assert_is_locked(fp.name, exclusive_lock=True,
            message='file %r should have a shared lock so we must not be able to lock it exclusively.' % temp_name)
        unlock(fp)
        if is_windows():
            # Windows does not allow opening the file twice so we need to close
            # it first.
            fp.close()
        self.assert_is_unlocked(temp_name)

    def assert_is_locked(self, filename, exclusive_lock=True, message=None):
        is_locked = self.is_locked(filename, exclusive_lock=exclusive_lock)
        assert_true(is_locked, message=(message or 'file %r should be locked' % filename))

    def assert_is_unlocked(self, filename):
        assert_false(self.is_locked(filename, exclusive_lock=True),
            message='file %r should be unlocked' % filename)

    def is_locked(self, filename, exclusive_lock):
        test_code = (
            'import sys;'
            'from ddc.storage.locking import acquire_lock;'
            'got_lock = acquire_lock(open(sys.argv[1]), exclusive_lock=%s, raise_on_error=False);'
            'sys.exit(got_lock == False);'
        ) % ('True' if exclusive_lock else 'False')
        python = sys.executable
        process = subprocess.Popen([python, '-c', test_code, filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        returncode = process.wait()
        sys.stdout.write(process.stdout.read().decode('utf8'))
        stderr = process.stderr.read().decode('utf8')
        if stderr:
            print(stderr)
            self.fail()
        # fs: sys.stdout.buffer didn't work when I ran this code using
        # nosetests on Windows XP (32 bit).
        #sys.stdout.buffer.write(process.stdout.read())
        return (returncode != 0)

