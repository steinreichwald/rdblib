# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from ddt import ddt as DataDrivenTestCase, data
from pythonic_testcase import *

from srw.rdblib.paths import DataBunch


@DataDrivenTestCase
class DataBunchTest(PythonicTestCase):
    @data('cdb', 'ibf', 'db') # but not 'ask'
    def test_is_complete(self, missing_attr):
        attrs = dict(cdb='foo.cdb', ibf='foo.ibf', db='foo.db', ask='foo.ask')
        assert_true(DataBunch(**attrs).is_complete())

        attrs[missing_attr] = None
        assert_false(DataBunch(**attrs).is_complete())

        attrs = dict(cdb='foo.cdb', ibf='foo.ibf', db='foo.db', ask=None)
        assert_true(DataBunch(**attrs).is_complete())

        attrs[missing_attr] = None
        assert_false(DataBunch(**attrs).is_complete())

    @data('cdb', 'ibf', 'db', 'ask')
    def test_can_merge_attributes(self, type_):
        attrs = dict(cdb='foo.cdb', ibf='foo.ibf', db='foo.db', ask='foo.ask')
        bunch = DataBunch(**attrs)

        merged = DataBunch.merge(bunch, **{type_: 'new.bin'})
        assert_equals('new.bin', getattr(merged, type_))

