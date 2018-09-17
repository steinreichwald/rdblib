# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from struct import pack
from unittest.mock import patch, Mock, MagicMock

from pythonic_testcase import *
import six
from srw.rdblib.tool.cdb_tool import (FormBatch, FormBatchHeader, FormHeader,
    Form, FormField)



def packhelper(fmt, *args):
    ''' convert strings to bytes before packing '''
    packargs = []
    for arg in args:
        if isinstance(arg, six.text_type):
            arg = arg.encode('cp850')
        packargs.append(arg)
    return pack(fmt, *packargs)

class TestFormBatchMethods(PythonicTestCase):

    def setUp(self):
        patcher = patch.object(FormBatch, '__init__', return_value=None)
        self.form_batch_init_mock = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch.object(FormBatchHeader, '__init__',
                               return_value=None)
        self.form_batch_header_init_mock = patcher.start()
        self.addCleanup(patcher.stop)

    def test_form_count(self):
        form_batch = FormBatch()

        form_batch_header = Mock()
        form_batch_header.rec.form_count = 300
        form_batch.form_batch_header = form_batch_header

        assert_equals(form_batch.count(), 300)

    @patch.object(FormBatch, 'count', return_value=300)
    def test_len(self, count_mock):
        form_batch = FormBatch()
        assert_length(300, form_batch)


class TestFormBatchHeader(PythonicTestCase):

    def setUp(self):
        self.batch_header_binary = self.create_batch_header()
        self.form_batch_header = FormBatchHeader(
            self.batch_header_binary)

    def test_create(self):
        rec = self.form_batch_header.rec
        assert_equals(rec.ibf_path, self.ibf_path)
        assert_equals(rec.ibf_format_string, self.ibf_format_string)
        assert_equals(rec.form_count, self.form_count)
        assert_equals(rec.next_form, self.next_form)
        assert_equals(rec.recognized_forms, self.recognized_forms)

    def test_get_binary(self):
        binary_result = self.form_batch_header._get_binary()
        assert_equals(binary_result, self.batch_header_binary)

    def test_getattr_normal_attribute(self):
        self.form_batch_header.dummy_value = 'dummy'
        assert_equals(self.form_batch_header.dummy_value, 'dummy')

    def test_getattr_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            self.form_batch_header.dummy_value

    def test_setattr_binary_field(self):
        self.form_batch_header.update_rec(form_count = 999)
        assert_equals(999, self.form_batch_header.rec.form_count)

    def create_batch_header(self):
        self.ibf_path = r'K:\WALTHER\SCAN\201001\00000001\00035100'
        self.ibf_format_string = '%s.IBF'
        self.form_count = 4
        self.next_form = 1
        self.recognized_forms = 2
        return packhelper('128s16siii',
                          self.ibf_path,
                          self.ibf_format_string,
                          self.form_count,
                          self.next_form,
                          self.recognized_forms)

class TestFormHeader(PythonicTestCase):

    def setUp(self):
        self.form_header_binary = self.create_form_header()
        self.form_header = FormHeader(
            self.form_header_binary, 0)

    def test_create(self):
        rec = self.form_header.rec
        assert_equals(rec.number_in_batch, self.number_in_batch)
        assert_equals(rec.status, self.status)
        assert_equals(rec.imprint_line_short, self.imprint_line_short)
        assert_equals(rec.field_count, self.field_count)
        assert_equals(rec.pharmacy_rejects, self.pharmacy_rejects)
        assert_equals(rec.doctor_rejects, self.doctor_rejects)
        ##assert_equals(rec.valid, self.valid)
        assert_equals(rec.left_margin, self.left_margin)
        assert_equals(rec.top_margin, self.top_margin)
        assert_equals(rec.right_margin, self.right_margin)
        assert_equals(rec.bottom_margin, self.bottom_margin)
        assert_equals(rec.rear_side, self.rear_side)
        assert_equals(rec.imprint_line_long, self.imprint_line_long)

    def test_get_binary(self):
        binary_result = self.form_header._get_binary()
        assert_equals(binary_result, self.form_header_binary)

    def create_form_header(self):
        self.number_in_batch = 1
        self.status = 2
        self.imprint_line_short = '00103500001024'
        self.field_count = 4
        self.pharmacy_rejects = 8
        self.doctor_rejects = 16
        self.valid = 32
        self.left_margin = 64
        self.top_margin = 128
        self.right_margin = 256
        self.bottom_margin = 512
        self.rear_side = 1024
        self.imprint_line_long = 'XXX00103500001024XXX'
        return packhelper('ii20siiiiiiiii80s16x',
                          self.number_in_batch,
                          self.status,
                          self.imprint_line_short,
                          self.field_count,
                          self.pharmacy_rejects,
                          self.doctor_rejects,
                          self.valid,
                          self.left_margin,
                          self.top_margin,
                          self.right_margin,
                          self.bottom_margin,
                          self.rear_side,
                          self.imprint_line_long)

class TestFormCreation(PythonicTestCase):

    @patch.object(Form, 'load_form_header', return_value=None)
    @patch.object(Form, 'load_form_fields', return_value=None)
    def test_create(self, mocked_load_form_fields,
                    mocked_load_form_header):
        self.filecontent = b'job_filecontent'
        offset = 5
        form = Form(self, offset)

        mocked_load_form_header.assert_called_once_with()
        mocked_load_form_fields.assert_called_once_with()
        assert_equals(form.record_size, 0)
        assert_equals(form.filecontent, self.filecontent)
        assert_equals(form.offset, offset)

class TestFormMethods(PythonicTestCase):

    def setUp(self):
        patcher = patch.object(Form, '__init__', return_value=None)
        self.form_init_mock = patcher.start()
        self.addCleanup(patcher.stop)

    @patch.object(FormHeader, '__init__', return_value=None)
    def test_load_form_header(self, mocked_form_header_init):
        filecontent = b'job_filecontent'
        offset = 2

        form = Form()
        self.filecontent = filecontent
        form.parent = self
        form.offset = offset

        form.load_form_header()

        mocked_form_header_init.assert_called_once_with(
            filecontent, offset)
        assert_isinstance(form.form_header, FormHeader)
        assert_equals(form.record_size, FormHeader.record_size)

    def _create_test_form(self,
                          form_header_record_size,
                          field_count,
                          field_record_size,
                          filecontent):
        form = Form()
        form.offset = 0
        form.record_size = form_header_record_size
        form.form_header = Mock()
        form.form_header.record_size = form_header_record_size
        form.form_header.rec.field_count = field_count
        self.filecontent = filecontent
        form.parent = self

        patcher = patch('ddc.tool.cdb_tool.FormField',
                        new=FormFieldMock)
        form_field_mock = patcher.start()
        self.addCleanup(patcher.stop)

        return form

    def test_getitem(self):
        field_name = 'FIELDNAME'
        field_value = 'value'
        form = Form()
        form.fields = {field_name: field_value}
        assert_equals(form[field_name], field_value)

    def test_get_pic_nr(self):
        pic_nr = '20309900001024'

        form = Form()
        form.form_header = Mock()
        form.form_header.rec.imprint_line_short = pic_nr
        assert_equals(pic_nr, form.pic_nr)

class TestFormField(PythonicTestCase):

    def setUp(self):
        self.form_field_binary = self.create_form_field()
        self.form_field = FormField(
            self.form_field_binary, 0)

    def test_create(self):
        rec = self.form_field.rec
        assert_equals(rec.number, self.number)
        assert_equals(rec.status, self.status)
        assert_equals(rec.name, self.name)
        assert_equals(rec.rejects, self.rejects)
        assert_equals(rec.recognizer_result, self.recognizer_result)
        assert_equals(rec.corrected_result, self.corrected_result)
        ##assert_equals(rec.valid, self.valid)
        assert_equals(rec.left, self.left)
        assert_equals(rec.top, self.top)
        assert_equals(rec.right, self.right)
        assert_equals(rec.bottom, self.bottom)

    def test_get_binary(self):
        binary_result = self.form_field._get_binary()
        assert_equals(binary_result, self.form_field_binary)

    def create_form_field(self):
        self.number = 1
        self.status = 2
        self.name = 'NAME'
        self.rejects = 4
        self.recognizer_result = 'RECOGNIZED RESULT'
        self.corrected_result = 'CORRECTED RESULT'
        self.valid = 8
        self.left = 16
        self.top = 32
        self.right = 64
        self.bottom = 128
        return packhelper('ii20si40s40siiiii',
                          self.number,
                          self.status,
                          self.name,
                          self.rejects,
                          self.recognizer_result,
                          self.corrected_result,
                          self.valid,
                          self.left,
                          self.top,
                          self.right,
                          self.bottom)

class FormMock(MagicMock):

    def __init__(self, *args, **kwargs):
        MagicMock.__init__(self, *args, **kwargs)
        self.record_size = 5

class FormFieldMock(MagicMock):

    last_number = 0

    def __init__(self, *args, **kwargs):
        MagicMock.__init__(self, *args, **kwargs)
        self.record_size = 5
        FormFieldMock.last_number += 1
        self.rec = Mock()
        self.rec.name = 'NAME' + str(FormFieldMock.last_number)

