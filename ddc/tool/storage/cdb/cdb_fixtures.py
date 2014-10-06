#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from ddc.dbdef import cdb_definition
from ddc.tool.storage.fixture_helpers import BinaryFixture


__all__ = ['CDBField', 'CDBFile', 'CDBForm']

cdb_format = cdb_definition.Form_Defn

class CDBFile(BinaryFixture):
    # TODO: support ibf_path, ibf_format_string, next_form, recognized_forms
    def __init__(self, forms, encoding=None):
        self.forms = forms
        values = dict(form_count=len(forms))
        super(CDBFile, self).__init__(values, cdb_format.batchheader_struc, encoding=encoding)

    def as_bytes(self, buffer_=None):
        buffer_ = super(CDBFile, self).as_bytes(self.values, buffer_=buffer_)
        for i, form in enumerate(self.forms):
            cdb_form = form
            if isinstance(form, dict):
                cdb_form = CDBForm(form, encoding=self.encoding)
            cdb_form.as_bytes(buffer_, batch_position=i)
        return buffer_


class CDBForm(BinaryFixture):
    def __init__(self, fields, batch_position=None, encoding=None, **values):
        self.fields = fields
        values.update(dict(
            number_in_batch=batch_position, field_count=len(fields)
        ))
        super(CDBForm, self).__init__(values, cdb_format.header_struc, encoding=encoding)

    def as_bytes(self, buffer_=None, batch_position=None):
        values_ = self.values.copy()
        if batch_position is not None:
            values_['number_in_batch'] = batch_position
        self._assert_caller_used_only_known_fields(values_, self.bin_structure)
        buffer_ = super(CDBForm, self).as_bytes(values_, buffer_=buffer_)
        for field in self.fields:
            cdb_field = CDBField(encoding=self.encoding, **field)
            cdb_field.as_bytes(buffer_)
        return buffer_


class CDBField(BinaryFixture):
    def __init__(self, name=None, corrected_result=None, encoding=None, **values):
        # I think it's a convenient API to use have name/"value" also as
        # positional parameters.
        values.update(dict(name=name, corrected_result=corrected_result))
        super(CDBField, self).__init__(values, cdb_format.field_struc, encoding=encoding)

    def as_bytes(self, buffer_=None):
        return super(CDBField, self).as_bytes(self.values, buffer_=buffer_)

