# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from io import BytesIO

from .cdb_format import CDBFormat
from ddc.storage.fixture_helpers import BinaryFixture, UnclosableBytesIO


__all__ = [
    'create_cdb_with_dummy_data',
    'create_cdb_with_form_values',
    'CDBField', 'CDBFile', 'CDBForm'
]

class CDBFile(BinaryFixture):
    # TODO: support ibf_path, ibf_format_string, next_form, recognized_forms
    def __init__(self, forms, encoding=None):
        self.forms = forms
        values = dict(form_count=len(forms))
        bin_structure = CDBFormat.batch_header
        super(CDBFile, self).__init__(values, bin_structure, encoding=encoding)

    def as_bytes(self):
        buffer_ = BytesIO()
        cdb_data = super(CDBFile, self).as_bytes(self.values)
        buffer_.write(cdb_data)
        for i, form in enumerate(self.forms):
            cdb_form = form
            if not hasattr(form, 'as_bytes'):
                cdb_form = CDBForm(form, encoding=self.encoding)
            form_data = cdb_form.as_bytes(batch_position=i)
            buffer_.write(form_data)
        buffer_.seek(0)
        return buffer_.read()


class CDBForm(BinaryFixture):
    def __init__(self, fields, batch_position=None, encoding=None, **values):
        self.fields = fields
        values_ = dict(
            number_in_batch=batch_position,
            field_count=len(fields),
        )
        values_.update(values)
        bin_structure = CDBFormat.form_header
        super(CDBForm, self).__init__(values_, bin_structure, encoding=encoding)

    def as_bytes(self, batch_position=None):
        values_ = self.values.copy()
        if batch_position is not None:
            values_['number_in_batch'] = batch_position
        self._assert_caller_used_only_known_fields(values_, self.bin_structure)

        buffer_ = BytesIO()
        form_data = super(CDBForm, self).as_bytes(values_)
        buffer_.write(form_data)
        for cdb_field in self.fields:
            if not hasattr(cdb_field, 'as_bytes'):
                cdb_field = CDBField(encoding=self.encoding, **cdb_field)
            field_data = cdb_field.as_bytes()
            buffer_.write(field_data)
        buffer_.seek(0)
        return buffer_.read()


class CDBField(BinaryFixture):
    def __init__(self, name=None, corrected_result=None, encoding=None, **values):
        # I think it's a convenient API to use have name/"value" also as
        # positional parameters.
        values.update(dict(name=name, corrected_result=corrected_result))
        bin_structure = CDBFormat.field
        super(CDBField, self).__init__(values, bin_structure, encoding=encoding)

    def as_bytes(self):
        return super(CDBField, self).as_bytes(self.values)


def create_cdb_with_dummy_data(nr_forms=1, filename=None):
    from ddc.validation.testutil import valid_prescription_values

    field = valid_prescription_values()
    form_values = (field,) * nr_forms
    return create_cdb_with_form_values(form_values, filename=filename)


def create_cdb_with_form_values(form_values, filename=None):
    """
    Generate a CDB based on the specified form values which is an iterable of
    dicts. Each dict contains the field names as keys and their corresponding
    "corrected result".
    If filename is None the data will be created in memory only. Otherwise the
    data will be written to the specified file.

    Returns a file-like object which contains the binary CDB data.
    """
    def _cdb_form_from_fields_data(fields_data):
        fields = []
        header_values = {}
        for field_name, field_value in fields_data.items():
            if field_name == 'pic':
                header_values['imprint_line_short'] = field_value
                continue
            field = {'name': field_name}
            if isinstance(field_value, str):
                field['corrected_result'] = field_value
            else:
                field.update(field_value)
            fields.append(field)
        return CDBForm(fields, **header_values)

    forms = []
    for fields_data in form_values:
        form = _cdb_form_from_fields_data(fields_data)
        forms.append(form)
    cdb_data = CDBFile(forms).as_bytes()
    if filename is None:
        return UnclosableBytesIO(cdb_data)
    cdb_fp = open(filename, 'ab+')
    # seek+truncate just in case the file already exists
    cdb_fp.seek(0, 0)
    cdb_fp.truncate()
    cdb_fp.write(cdb_data)
    cdb_fp.seek(0, 0)
    return cdb_fp

