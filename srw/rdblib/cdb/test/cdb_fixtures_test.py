# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from io import BytesIO

from pythonic_testcase import *

from ..cdb_fixtures import create_cdb_with_dummy_data, CDBFile, CDBForm
from ...testutil import VALIDATED_FIELDS
from ...tool.cdb_tool import FormBatch


class CDBFileTest(PythonicTestCase):
    def test_can_generate_cdb_file_with_single_form(self):
        # use direct access to CDBForm/CDBFile instead of the helper function
        # to get a better view on the lower-level classes even though they are
        # exercised by the helpers as well.
        fields = []
        ALL_FIELD_NAMES = ('STRASSE', 'WOHNORT')
        for field_name in ALL_FIELD_NAMES:
            fields.append({'name': field_name, 'corrected_result': 'baz'})
        cdb_form = CDBForm(fields)
        cdb_batch = CDBFile([cdb_form])
        cdb_fp = BytesIO(cdb_batch.as_bytes())

        batch = FormBatch(cdb_fp, access='read', field_names=ALL_FIELD_NAMES)
        assert_equals(1, batch.count())
        form = batch.forms[0]
        assert_equals('baz', form['STRASSE'].corrected_result)

    def test_create_cdb_helper_function(self):
        cdb_fp = create_cdb_with_dummy_data(nr_forms=3, field_names=VALIDATED_FIELDS)
        cdb_batch = FormBatch(cdb_fp, access='read', field_names=VALIDATED_FIELDS)
        assert_equals(3, len(cdb_batch))

    def test_can_generate_form_with_specified_pic(self):
        pic = '12345600114024'
        fields = [
            {'name': 'AUSSTELLUNGSDATUM', 'corrected_result': 'baz'}
        ]
        cdb_form = CDBForm(fields, imprint_line_short=pic)
        cdb_fp = BytesIO(CDBFile([cdb_form]).as_bytes())

        batch = FormBatch(cdb_fp, access='read', field_names=('AUSSTELLUNGSDATUM',))
        assert_equals(1, batch.count())
        form = batch.forms[0]
        assert_equals(pic, form.pic_nr)

    def test_can_generate_deleted_forms(self):
        fields = [
            {'name': 'AUSSTELLUNGSDATUM', 'corrected_result': 'baz'}
        ]
        cdb_form = CDBForm(fields, imprint_line_short='DELETED')
        cdb_fp = BytesIO(CDBFile([cdb_form]).as_bytes())

        batch = FormBatch(cdb_fp, access='read', field_names=('AUSSTELLUNGSDATUM',))
        assert_equals(1, batch.count())
        form = batch.forms[0]
        assert_true(form.is_deleted())
        assert_equals('DELETED', form.pic_nr)

