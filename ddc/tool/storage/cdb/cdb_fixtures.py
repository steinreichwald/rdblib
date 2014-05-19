#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from io import BytesIO
import struct

from ddc.dbdef import cdb_definition


__all__ = ['CDBField', 'CDBFile', 'CDBForm']

cdb_format = cdb_definition.Form_Defn

class CDBFixture(object):
    def __init__(self, values, bin_structure, encoding=None):
        self.values = values
        self.bin_structure = bin_structure
        self.encoding = encoding or cdb_definition.encoding
        self._assert_caller_used_only_known_fields()

    def _assert_caller_used_only_known_fields(self):
        known_field_names = set(dict(self.bin_structure))
        unknown_values = set(self.values).difference(known_field_names)
        if unknown_values:
            unknown_field = unknown_values.pop()
            raise TypeError('unknown CDB field %r' % unknown_field)

    def as_bytes(self, buffer_=None):
        if buffer_ is None:
            buffer_ = BytesIO()
        for i, (key, format_) in enumerate(self.bin_structure):
            if key in self.values:
                value = self.values[key]
            elif key == 'number':
                value = i+1
            elif format_.endswith('s'):
                value = ''
            elif format_.endswith('i'):
                value = 0
            else:
                raise AssertionError('unexpected binary format')
            if isinstance(value, basestring):
                value = value.encode(self.encoding)
            bin_ = struct.pack(format_, value)
            buffer_.write(bin_)
        return buffer_


class CDBFile(CDBFixture):
    # TODO: support ibf_path, ibf_format_string, next_form, recognized_forms
    def __init__(self, forms, encoding=None):
        self.forms = forms
        values = dict(form_count=len(forms))
        super(CDBFile, self).__init__(values, cdb_format.batchheader_struc, encoding=encoding)

    def as_bytes(self, buffer_=None):
        buffer_ = super(CDBFile, self).as_bytes(buffer_=buffer_)
        for i, form in enumerate(self.forms):
            cdb_form = form
            if isinstance(form, dict):
                cdb_form = CDBForm(form, encoding=self.encoding)
            cdb_form.as_bytes(buffer_, batch_position=i)
        return buffer_


class CDBForm(CDBFixture):
    def __init__(self, fields, batch_position=None, encoding=None, **values):
        self.fields = fields
        values.update(dict(
            number_in_batch=batch_position, field_count=len(fields)
        ))
        super(CDBForm, self).__init__(values, cdb_format.header_struc, encoding=encoding)

    def as_bytes(self, buffer_=None, batch_position=None):
        if batch_position is not None:
            self.values['number_in_batch'] = batch_position
        buffer_ = super(CDBForm, self).as_bytes(buffer_=buffer_)
        for field in self.fields:
            cdb_field = CDBField(encoding=self.encoding, **field)
            cdb_field.as_bytes(buffer_)
        return buffer_


class CDBField(CDBFixture):
    def __init__(self, name=None, corrected_result=None, encoding=None, **values):
        # I think it's a convenient API to use have name/"value" also as
        # positional parameters.
        values.update(dict(name=name, corrected_result=corrected_result))
        super(CDBField, self).__init__(values, cdb_format.field_struc, encoding=encoding)

