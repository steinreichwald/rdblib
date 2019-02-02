# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import multiprocessing
import os

from pythonic_testcase import *

from ..lib.fake_fs_utils import FakeFS, TempFS
from ..paths import assemble_new_path, safe_move


class SafeMoveTest(PythonicTestCase):
    def test_handles_source_equals_target(self):
        fs = FakeFS.set_up(test=self)
        path = os.path.join(fs.root.name, 'foo')
        fs.create_file(path)
        with assert_not_raises():
            safe_move(path, path)

    def test_read(self):
        # FakeFS won't work properly after creating a new process
        fs = TempFS.set_up(test=self)
        path = os.path.join(fs.root, 'foo.bin')
        fs.create_file(path, contents=b'x')
        new_path = assemble_new_path(path, new_extension='.bak')

        assert_no_timeout(safe_move, path, new_path, timeout_seconds=2)


def assert_no_timeout(func, *args, timeout_seconds=None, **kwargs):
    assert timeout_seconds
    process = multiprocessing.Process(None, func, None, args, kwargs)
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        raise AssertionError('function call took longer than %s seconds' % timeout_seconds)
