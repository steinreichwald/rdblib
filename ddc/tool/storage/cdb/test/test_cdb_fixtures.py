# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from io import BytesIO

from pythonic_testcase import *

from ddc.client.config.config_base import FieldList
from ddc.tool.cdb_tool import FormBatch
from ddc.tool.storage.cdb.cdb_fixtures import create_cdb_with_dummy_data, CDBFile, CDBForm


class CDBFileTest(PythonicTestCase):
    def test_can_generate_cdb_file_with_single_form(self):
        field_names = [field_class.link_name for field_class in FieldList(None)]
        fields = []
        for field_name in field_names:
            fields.append({'name': field_name, 'corrected_result': 'baz'})
        cdb_form = CDBForm(fields)
        cdb_batch = CDBFile([cdb_form])
        cdb_fp = BytesIO(cdb_batch.as_bytes())

        batch = FormBatch(cdb_fp, access='read')
        assert_equals(1, batch.count())
        form = batch.forms[0]
        assert_equals('baz', form['STRASSE'].corrected_result)

    def test_create_cdb_helper_function(self):
        cdb_fp = create_cdb_with_dummy_data(nr_forms=3)
        cdb_batch = FormBatch(cdb_fp, access='read')
        assert_equals(3, len(cdb_batch))

