# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import os
import shutil
from tempfile import mkdtemp

from pythonic_testcase import *

from ddc.client.config import ALL_FIELD_NAMES
from ddc.storage.cdb import (
    create_cdb_with_dummy_data,
    create_cdb_with_form_values,
    Field, FormHeader,
    open_cdb,
)
from ddc.storage.locking import acquire_lock
from ddc.tool.cdb_tool import FormBatch
from ddc.validation.testutil import valid_prescription_values


class CDBCheckTest(PythonicTestCase):
    def setUp(self):
        super(CDBCheckTest, self).setUp()
        self.env_dir = mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.env_dir)
        super(PythonicTestCase, self).tearDown()

    def test_can_return_cdb_instance(self):
        cdb_path = os.path.join(self.env_dir, 'foo.cdb')
        cdb_fp = create_cdb_with_dummy_data(nr_forms=1, filename=cdb_path)
        cdb_fp.close()

        result = open_cdb(cdb_path, field_names=ALL_FIELD_NAMES)
        assert_true(result)
        assert_not_none(result.cdb_fp)

        cdb = FormBatch(result.cdb_fp)
        assert_equals(1, cdb.count())
        cdb.close()

    def test_can_detect_locked_cdb_files(self):
        cdb_path = os.path.join(self.env_dir, 'foo.cdb')
        cdb_fp = create_cdb_with_dummy_data(nr_forms=1, filename=cdb_path)
        acquire_lock(cdb_fp, exclusive_lock=True, raise_on_error=True)

        result = open_cdb(cdb_path, field_names=ALL_FIELD_NAMES)
        assert_false(result)
        assert_none(result.cdb_fp)
        assert_contains('noch in Bearbeitung.', result.message)

        cdb_fp.close()

    def test_can_detect_cdb_files_with_trailing_junk(self):
        cdb_path = os.path.join(self.env_dir, 'foo.cdb')
        cdb_fp = create_cdb_with_dummy_data(nr_forms=1, filename=cdb_path)
        cdb_fp.seek(0, os.SEEK_END)
        cdb_fp.write(b'\x00' * 100)
        cdb_fp.close()

        result = open_cdb(cdb_path, field_names=ALL_FIELD_NAMES)
        assert_false(result)
        assert_none(result.cdb_fp)
        assert_contains(u'ungewöhnliche Größe', result.message)

    def test_can_detect_cdb_files_with_bad_formcount_in_header(self):
        cdb_path = os.path.join(self.env_dir, 'foo.cdb')
        cdb_fp = create_cdb_with_dummy_data(nr_forms=1, filename=cdb_path)
        nr_fields_per_form = len(valid_prescription_values())
        bytes_per_form = FormHeader.size + (nr_fields_per_form * Field.size)
        # simulate a (faulty) form so the total file size is ok but the sanity
        # checker should detect that condition before parsing the fields.
        cdb_fp.seek(0, os.SEEK_END)
        cdb_fp.write(b'\x00' * bytes_per_form)
        cdb_fp.close()

        result = open_cdb(cdb_path, field_names=ALL_FIELD_NAMES)
        assert_false(result)
        assert_none(result.cdb_fp)
        expected_msg = u'Die Datei enthält 1 Belege (Header), es müssten 2 Belege vorhanden sein (Dateigröße).'
        assert_contains(expected_msg, result.message)

    def test_can_detect_forms_with_unusual_number_of_fields(self):
        cdb_path = os.path.join(self.env_dir, 'foo.cdb')
        fields_form1 = valid_prescription_values()
        nr_fields1 = len(fields_form1)
        # form #2 has one field less and form #3 one extra field so the total
        # file size looks ok
        fields_form2 = valid_prescription_values()
        first_field_name = tuple(fields_form2)[0]
        del fields_form2[first_field_name]
        nr_fields2 = len(fields_form2)
        fields_form3 = valid_prescription_values(extra='anything')
        assert_not_equals(nr_fields1, nr_fields2,
            message='Form #2 should have an unusual number of fields.')
        cdb_forms = (fields_form1, fields_form2, fields_form3)
        cdb_fp = create_cdb_with_form_values(cdb_forms, filename=cdb_path)
        cdb_fp.close()

        result = open_cdb(cdb_path, field_names=ALL_FIELD_NAMES)
        assert_false(result)
        assert_none(result.cdb_fp)
        expected_msg = u'Formular #2 ist vermutlich fehlerhaft (%d Felder statt %d)'
        assert_contains(expected_msg % (nr_fields2, nr_fields1), result.message)

    def test_can_detect_forms_with_unknown_field_names(self):
        cdb_path = os.path.join(self.env_dir, 'foo.cdb')
        fields_form1 = valid_prescription_values()
        first_field_name = tuple(fields_form1)[0]
        del fields_form1[first_field_name]
        fields_form1['extra'] = 'anything'
        cdb_forms = (fields_form1,)
        cdb_fp = create_cdb_with_form_values(cdb_forms, filename=cdb_path)
        cdb_fp.close()

        result = open_cdb(cdb_path, field_names=ALL_FIELD_NAMES)
        assert_false(result)
        assert_none(result.cdb_fp)
        expected_msg = u'Formular #1 ist vermutlich fehlerhaft (unbekanntes Feld b\'extra\').'
        assert_contains(expected_msg, result.message)
