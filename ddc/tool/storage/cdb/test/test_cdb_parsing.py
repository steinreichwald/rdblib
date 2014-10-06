#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from io import BytesIO
from unittest.case import TestCase

from ddc.client.config.config_base import FieldList
from ddc.tool.cdb_tool import FormBatch
from ddc.tool.storage.cdb.cdb_fixtures import CDBFile, CDBForm


class CDBParsing(TestCase):
    def test_raises_error_if_cdb_file_contains_form_with_overwritten_fields(self):
        # prevent parsing of CDB files with overwritten field names. See also
        # further information in Form (cdb_tool.py) and pydica issue 10.
        field_names = [field_class.link_name for field_class in FieldList(None)]
        first_field = field_names[0]
        second_field = field_names[1]
        bad_field_name = u'INVALID'
        # CDB files with overwritten structures can only by detected by
        # checking for unknown fields names (usually junk like '+++++…' or so)
        self.assertFalse(bad_field_name in field_names)
        fields = [
            {'name': first_field, 'corrected_result': 'baz'},
            {'name': bad_field_name, 'corrected_result': 'random stuff'},
            {'name': second_field, 'corrected_result': 'foo'},
        ]
        cdb_form = CDBForm(fields)
        cdb_data = CDBFile([cdb_form]).as_bytes()
        with self.assertRaises(ValueError):
            FormBatch(BytesIO(cdb_data), access='read')

    def test_raises_error_if_cdb_contains_forms_with_varying_field_counts(self):
        # The Form parsing code assumes that all forms have the same size. This
        # is always true for real data files and enables fast data access.
        # However the parser should catch all cases where this assumption is
        # not true.
        field_names = [field_class.link_name for field_class in FieldList(None)]
        first_field = field_names[0]
        fields = [{'name': first_field, 'corrected_result': 'foo'}]
        # Test scenario: first form has no fields, second form one field
        first_form = CDBForm([])
        second_form = CDBForm(fields)
        cdb_data = CDBFile([first_form, second_form]).as_bytes()

        with self.assertRaises(TypeError) as cm:
            FormBatch(BytesIO(cdb_data), access='read')
        e = cm.exception
        # Testing the exception here so we are sure we're triggering the right
        # safeguard.
        self.assertEquals('wrong form record size, this is no CDB', str(e))

    def test_can_handle_forms_exceptionally_large_field_count_entry(self):
        field_names = [field_class.link_name for field_class in FieldList(None)]
        first_field = field_names[0]
        fields = [{'name': first_field, 'corrected_result': 'foo'}]
        form = CDBForm(fields, field_count=1431197259)
        cdb_data = CDBFile([form]).as_bytes()

        with self.assertRaises(ValueError) as cm:
            FormBatch(BytesIO(cdb_data), access='read')
        e = cm.exception
        # Testing the exception here so we are sure we're triggering the right
        # safeguard.
        expected_msg = 'offset + record_size exceeds file size!'
        self.assertTrue(str(e).startswith(expected_msg))

