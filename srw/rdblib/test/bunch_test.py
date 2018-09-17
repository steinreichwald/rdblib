# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from pythonic_testcase import *
from srw.rdblib import DataBunch



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
