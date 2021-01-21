# -*- coding: UTF-8 -*-
# SPDX-License-Identifier: MIT or BSD-3-Clause

from pythonic_testcase import *

from ..bindiff import format_diff_line, ChangeGroup


class BinDiffFormatDiffLineTest(PythonicTestCase):
    def test_format_diff_line(self):
        line_parts = format_diff_line('+', 'pho baz', [(0, 2), (6, 6)])
        assert_length(4, line_parts)
        c_prefix, c_pho, uc_middle, c_z = line_parts
        assert_equals(ChangeGroup('+ ', True), c_prefix)
        assert_equals(ChangeGroup('pho', True), c_pho)
        assert_equals(ChangeGroup(' ba', False), uc_middle)
        assert_equals(ChangeGroup('z', True), c_z)

    def test_format_diff_line_with_tail_difference(self):
        line_parts = format_diff_line('-', 'foo baz', [(6, 6)])
        assert_length(3, line_parts)
        c_prefix, uc_fooba, c_z = line_parts
        assert_equals(ChangeGroup('- ', True), c_prefix)
        assert_equals(ChangeGroup('foo ba', False), uc_fooba)
        assert_equals(ChangeGroup('z', True), c_z)

    def test_format_diff_line_with_same_tail(self):
        line_parts = format_diff_line('+', 'foo baz', [(0, 3)])
        assert_length(3, line_parts)
        c_prefix, uc_foo, c_baz = line_parts
        assert_equals(ChangeGroup('+ ', True), c_prefix)
        assert_equals(ChangeGroup('foo ', True), uc_foo)
        assert_equals(ChangeGroup('baz', False), c_baz)

