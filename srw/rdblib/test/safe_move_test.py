# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import os

from pythonic_testcase import *

from ..lib.fake_fs_utils import FakeFS
from ..paths import safe_move


class SafeMoveTest(PythonicTestCase):
    def test_handles_source_equals_target(self):
        fs = FakeFS.set_up(test=self)
        path = os.path.join(fs.root.name, 'foo')
        fs.create_file(path)
        with assert_not_raises():
            safe_move(path, path)

