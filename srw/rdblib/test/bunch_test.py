# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from ddt import ddt as DataDrivenTestCase, data
from pythonic_testcase import *
from srw.rdblib import DataBunch


@DataDrivenTestCase
class BunchTest(PythonicTestCase):
    def test_can_instantiate_with_positional_parameters(self):
        bunch = DataBunch('cdb', 'ibf', 'db', 'ask')
        self.assert_all_fields_are_filled(bunch)

    def test_can_instantiate_with_keyword_parameters(self):
        bunch = DataBunch(cdb='cdb', ibf='ibf', db='db', ask='ask')
        self.assert_all_fields_are_filled(bunch)

    @expect_failure
    def test_has_constructor_with_optional_arguments(self):
        bunch = DataBunch()
        assert_none(bunch.cdb)
        assert_none(bunch.ibf)
        assert_none(bunch.db)
        assert_none(bunch.ask)

        bunch = DataBunch(cdb='cdb')
        assert_equals('cdb', bunch.cdb)
        assert_none(bunch.ibf)

    def assert_all_fields_are_filled(self, bunch):
        for field_name in bunch._fields:
            assert_equals(field_name, getattr(bunch, field_name))

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
