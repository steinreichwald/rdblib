# -*- coding: UTF-8 -*-
# SPDX-License-Identifier: MIT or BSD-3-Clause

from pythonic_testcase import *

from ..bindiff import find_differences


class BinDiffFindDifferences(PythonicTestCase):
    def test_can_find_differences(self):
        assert_equals([(0, 2)], find_differences('foo', 'bar'))
        assert_equals([(2, 2)], find_differences('bar', 'baz'))
        assert_equals([(6, 6)], find_differences('foo bar', 'foo baz'))
        assert_equals([(4, 6)], find_differences('foo qux', 'foo bar'))

