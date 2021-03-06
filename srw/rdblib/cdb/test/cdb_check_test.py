# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from io import BytesIO
import os

from ddt import ddt as DataDrivenTestCase, data
from pythonic_testcase import *
from schwarz.fakefs_helpers import TempFS

from .. import (
    create_cdb_with_dummy_data,
    create_cdb_with_form_values,
    open_cdb,
)
from ..cdb_check import calculate_bytes_per_form, calculate_filesize
from ..cdb_fixtures import CDBFile, CDBForm
from ...locking import acquire_lock
from ...tool.cdb_tool import FormBatch
from ...testutil import valid_prescription_values, VALIDATED_FIELDS


@DataDrivenTestCase
class CDBCheckTest(PythonicTestCase):
    def setUp(self):
        self.fs = TempFS.set_up(test=self)
        self.env_dir = self.fs.create_directory('envdir')

    @data(True, False)
    def test_can_return_cdb_instance(self, explicit_fieldnames):
        cdb_path = os.path.join(self.env_dir, 'foo.cdb')
        form_fields = valid_prescription_values(with_pic=True)
        cdb_fp = create_cdb_with_form_values([form_fields], filename=cdb_path)
        cdb_fp.close()

        field_names = VALIDATED_FIELDS if explicit_fieldnames else None
        result = open_cdb(cdb_path, field_names=field_names)
        assert_true(result)
        assert_not_none(result.cdb_fp)

        cdb = FormBatch(result.cdb_fp)
        assert_equals(1, cdb.count())
        cdb.close()

    def test_can_handle_file_like_instance(self):
        cdb_path = os.path.join(self.env_dir, 'foo.cdb')
        form_fields = valid_prescription_values(with_pic=True)
        cdb_fp = create_cdb_with_form_values([form_fields], filename=cdb_path)
        cdb_bytes= cdb_fp.read()

        result = open_cdb(BytesIO(cdb_bytes))
        assert_true(result)

    def test_can_ensure_all_required_field_names_are_present(self):
        cdb_path = os.path.join(self.env_dir, 'foo.cdb')
        form_fields = valid_prescription_values(with_pic=True)
        cdb_fp = create_cdb_with_form_values([form_fields], filename=cdb_path)
        cdb_fp.close()
        required_fields = tuple(form_fields)[:2]
        assert_not_equals(tuple(form_fields), required_fields)

        result = open_cdb(cdb_path, required_fields=required_fields)
        assert_true(result, message='all required fields are present, should work as expected')
        result.cdb_fp.close()

        result = open_cdb(cdb_path, required_fields=required_fields + ('NONEXISTENT',))
        assert_false(result, message='field "NONEXISTENT" is not present in CDB')
        assert_equals('form.missing_field', result.key)
        assert_equals(0, result.form_index)
        assert_none(result.field_index)

    def test_can_detect_locked_cdb_files(self):
        cdb_path = os.path.join(self.env_dir, 'foo.cdb')
        cdb_fp = create_cdb_with_dummy_data(nr_forms=1, filename=cdb_path, field_names=VALIDATED_FIELDS)
        acquire_lock(cdb_fp, exclusive_lock=True, raise_on_error=True)

        result = open_cdb(cdb_path, field_names=VALIDATED_FIELDS)
        assert_false(result)
        assert_none(result.cdb_fp)
        assert_contains('noch in Bearbeitung.', result.message)
        assert_equals('file.is_locked', result.key)
        assert_none(result.form_index)
        assert_none(result.field_index)

        cdb_fp.close()

    @data(True, False)
    def test_can_detect_cdb_files_with_trailing_junk(self, explicit_fieldnames):
        cdb_path = self._create_cdb(nr_forms=1, nr_junk_bytes=100)

        field_names = VALIDATED_FIELDS if explicit_fieldnames else None
        result = open_cdb(cdb_path, field_names=field_names)
        assert_false(result)
        assert_none(result.cdb_fp)
        assert_contains(u'ungew??hnliche Gr????e', result.message)
        assert_equals('file.junk_after_last_record', result.key)
        assert_none(result.form_index)
        assert_none(result.field_index)

    @data(True, False)
    def test_can_detect_cdb_files_with_trailing_junk_forms(self, explicit_fieldnames):
        nr_forms_in_cdb = 3
        nr_junk_forms = 1
        nr_fields = len(VALIDATED_FIELDS)
        # test setup: if there are more/less validated fields we may have to
        # adapt the number of forms in the cdb/junk forms so validation really
        # fails with the expected error message.
        if nr_fields != 5:
            # nosetests will show this message only when the test fails...
            print('number of fields per form changed, may need to adapt variables')

        nr_junk_bytes = nr_junk_forms * calculate_bytes_per_form(nr_fields)
        cdb_path = self._create_cdb(nr_forms_in_cdb, nr_junk_bytes=nr_junk_bytes)

        field_names = VALIDATED_FIELDS if explicit_fieldnames else None
        result = open_cdb(cdb_path, field_names=field_names)
        assert_false(result)
        assert_none(result.cdb_fp)
        assert_equals('file.junk_after_last_record', result.key, message=result.message)
        # Need to test the error messages in detail to ensure that the error
        # message is as helpful as possible.
        if explicit_fieldnames:
            # error message mentions exact number of junk bytes (as we passed the correct field count)
            assert_equals(
                'Die CDB hat eine ungew??hnliche Gr????e (mindestens %d Bytes zu viel bei %d Belegen laut Header)' % (nr_junk_bytes, nr_forms_in_cdb),
                result.message
            )
        else:
            # code has to guess the number of fields but it points at least in
            # the right direction.
            assert_equals(
                'Die CDB hat eine ungew??hnliche Gr????e (mindestens 28 Bytes zu viel bei %d Belegen laut Header)' % nr_forms_in_cdb,
                result.message
            )
        assert_none(result.form_index)
        assert_none(result.field_index)

    def test_can_detect_cdb_files_with_trailing_junk_when_guessing_field_names(self):
        nr_forms_in_cdb = 1
        nr_fields = len(VALIDATED_FIELDS)
        # Carefully craft a RDB file where the filesize matches a "valid" file
        # with exactly one more field per form. This should trigger a helpful
        # error message with the exact number of junk bytes to facilitate
        # repairs.
        nr_junk_bytes = calculate_filesize(nr_forms_in_cdb, nr_fields+1) - calculate_filesize(nr_forms_in_cdb, nr_fields)
        cdb_path = self._create_cdb(nr_forms_in_cdb, nr_junk_bytes=nr_junk_bytes, field_names=VALIDATED_FIELDS)

        result = open_cdb(cdb_path, field_names=None)
        assert_false(result)
        assert_none(result.cdb_fp)
        assert_equals('form.unusual_number_of_fields', result.key, message=result.message)
        assert_equals(
            'Formular #1 enth??lt %d Felder, erwartet wurden aber %d (oder %d extra Bytes?).' % (nr_fields, nr_fields+1, nr_junk_bytes),
            result.message
        )
        assert_equals(0, result.form_index)
        assert_none(result.field_index)

    @data(True, False)
    def test_can_detect_forms_with_unusual_number_of_fields(self, explicit_fieldnames):
        cdb_path = os.path.join(self.env_dir, 'foo.cdb')
        fields_form1 = valid_prescription_values(with_pic=True)
        nr_fields1 = len(fields_form1) - 1 # -1 because of PIC
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

        field_names = VALIDATED_FIELDS if explicit_fieldnames else None
        result = open_cdb(cdb_path, field_names=field_names)
        assert_false(result)
        assert_none(result.cdb_fp)
        expected_msg = u'Formular #2 ist vermutlich fehlerhaft (%d Felder statt %d)'
        assert_contains(expected_msg % (nr_fields2, nr_fields1), result.message)
        assert_equals('form.unusual_number_of_fields', result.key)
        assert_equals(1, result.form_index)
        assert_none(result.field_index)

    def test_can_detect_forms_with_unknown_field_names(self):
        cdb_path = os.path.join(self.env_dir, 'foo.cdb')
        fields_form1 = valid_prescription_values()
        missing_fieldname = 'ABGABEDATUM'
        del fields_form1[missing_fieldname]
        fields_form1['extra'] = 'anything'
        cdb_forms = (fields_form1,)
        cdb_fp = create_cdb_with_form_values(cdb_forms, filename=cdb_path)
        cdb_fp.close()

        result = open_cdb(cdb_path, field_names=VALIDATED_FIELDS)
        assert_false(result)
        assert_none(result.cdb_fp)
        assert_contains(
            u'Formular #1 ist vermutlich fehlerhaft (unbekanntes Feld b\'extra\', fehlendes Feld b%r).' % missing_fieldname,
            result.message
        )
        assert_equals('form.unknown_fields', result.key)
        assert_equals(0, result.form_index)
        assert_equals(len(fields_form1)-1, result.field_index)

    @data(True, False)
    def test_can_detect_forms_with_empty_pic(self, explicit_fieldnames):
        cdb_path = os.path.join(self.env_dir, 'foo.cdb')
        fields = []
        for field_name, field_value in valid_prescription_values().items():
            field = {'name': field_name, 'corrected_result': field_value}
            fields.append(field)
        forms = [CDBForm(fields, imprint_line_short=b'')]
        cdb_bytes = CDBFile(forms).as_bytes()
        with open(cdb_path, 'wb') as fp:
            fp.write(cdb_bytes)

        field_names = VALIDATED_FIELDS if explicit_fieldnames else None
        result = open_cdb(cdb_path, field_names=field_names)
        assert_true(result,
            message='empty PIC numbers should be treated as warnings (can recover them from IBF)')
        assert_not_none(result.cdb_fp)
        assert_length(1, result.warnings)
        assert_equals(
            u'Formular #1 ist wahrscheinlich fehlerhaft (keine PIC-Nr vorhanden)',
            result.warnings[0]
        )
        assert_none(result.key)
        assert_none(result.form_index)
        assert_none(result.field_index)

    # --- helpers -------------------------------------------------------------
    def _create_cdb(self, nr_forms, *, nr_junk_bytes=0, field_names=None):
        if field_names is None:
            field_names= VALIDATED_FIELDS
        cdb_path = os.path.join(self.env_dir, 'foo.cdb')
        cdb_fp = create_cdb_with_dummy_data(nr_forms=nr_forms, filename=cdb_path, field_names=field_names)
        if nr_junk_bytes:
            cdb_fp.seek(0, os.SEEK_END)
            cdb_fp.write(b'\x00' * nr_junk_bytes)
        cdb_fp.close()
        return cdb_path
