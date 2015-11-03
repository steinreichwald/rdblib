# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from io import BytesIO

from ddc.dbdef import cdb_definition
from ddc.tool.storage.fixture_helpers import BinaryFixture, UnclosableBytesIO
from ddc.client.config.config_base import FieldList


__all__ = [
    'create_cdb_with_dummy_data',
    'create_cdb_with_form_values',
    'CDBField', 'CDBFile', 'CDBForm'
]


cdb_format = cdb_definition.Form_Defn

class CDBFile(BinaryFixture):
    # TODO: support ibf_path, ibf_format_string, next_form, recognized_forms
    def __init__(self, forms, encoding=None):
        self.forms = forms
        values = dict(form_count=len(forms))
        bin_structure = cdb_format.batchheader_struc
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
        bin_structure = cdb_format.header_struc
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
        bin_structure = cdb_format.field_struc
        super(CDBField, self).__init__(values, bin_structure, encoding=encoding)

    def as_bytes(self):
        return super(CDBField, self).as_bytes(self.values)


def create_cdb_with_dummy_data(nr_forms=1):
    field_names = [field_class.link_name for field_class in FieldList(None)]
    field = {'name': field_names[0], 'corrected_result': 'baz'}

    forms = [CDBForm([field]) for i in range(nr_forms)]
    cdb_data = CDBFile(forms).as_bytes()
    return UnclosableBytesIO(cdb_data)


def create_cdb_with_form_values(form_values):
    """
    Generate a CDB in memory based on the specified form values which is an
    iterable of dicts. Each dict contains the field names as keys and their
    corresponding "corrected result".
    Returns a file-like object which contains the binary CDB data.
    """
    forms = []
    for fields_data in form_values:
        fields = []
        for field_name, field_value in fields_data.items():
            field = {'name': field_name, 'corrected_result': field_value}
            fields.append(field)
        form = CDBForm(fields)
        forms.append(form)
    cdb_data = CDBFile(forms).as_bytes()
    return UnclosableBytesIO(cdb_data)

