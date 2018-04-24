# -*- coding: utf-8 -*-
"""
classes for dealing with prescription-files
"""
from __future__ import division, absolute_import, print_function, unicode_literals

import os
import warnings

from ddc.client.config import ALL_FIELD_NAMES
from ddc.storage import filecontent, MMapFile
from ddc.storage.cdb import CDBFormat
from ddc.storage.meta import WithBinaryMeta


########################################################################

class FormBatchHeader(WithBinaryMeta):
    _struc = CDBFormat.batch_header


class FormHeader(WithBinaryMeta):
    _struc = CDBFormat.form_header


class FormBatch(object):

    def __init__(self, batch_file, delay_load=False, access='write', log=None):
        assert delay_load == False
        if not hasattr(batch_file, 'close'):
            # the regular case, given a file name.
            batch_filename = batch_file
            self.mmap_file = MMapFile(batch_filename, access=access, log=log)
        else:
            # an already opened file, mostly meant for testing.
            # XXX should be cleaned: access is always passed, but ignored.
            self.mmap_file = batch_file

        self.form_batch_header = None
        self.forms = None

        self.load_form_batch_header()
        self._load_delayed = delay_load
        self.load_forms()

    def commit(self):
        for form in self.forms:
            if form.is_dirty():
                form.write_back()

    def close(self, commit=False):
        if commit:
            self.commit()
        self.mmap_file.close()

    @property
    def filecontent(self):
        return filecontent(self.mmap_file)

    @property
    def batch_filename(self):
        return self.mmap_file.name

    @property
    def job_nummer(self):
        filename = os.path.split(self.batch_filename)[1]
        return int(filename[5:8])

    @property
    def apo_nummer(self):
        filename = os.path.split(self.batch_filename)[1]
        return int(filename[0:5])

    def load_form_batch_header(self):
        self.form_batch_header = FormBatchHeader(self.filecontent)

    def load_forms(self):
        self.forms = LazyList()
        offset = self.form_batch_header.record_size
        # optimization:
        # we calculate the record size only once.
        first_header = FormHeader(self.filecontent, offset)
        field_count = first_header.rec.field_count
        record_size = (first_header.record_size +
                       Form._field_record_size * field_count)
        while offset < len(self.filecontent):
            form = self._build_form(offset, record_size)
            self.forms.append(form)
            offset += record_size
            if len(self.forms) > len(self):
                raise ValueError('prescription count exceeds header info')
        if len(self.forms) != len(self):
            raise ValueError("read prescription count (%d) differs from header info (%d)" % (len(self.forms), len(self)))

    def _build_form(self, offset, record_size):
        def form(self=self, offset=offset, record_size = record_size):
            form = Form(self, offset)
            if form.record_size != record_size:
                raise TypeError('wrong form record size, this is no CDB')
            known_fields = ALL_FIELD_NAMES
            unknown_fields = set(form._field_names).difference(set(known_fields))
            # The old software sometimes writes junk for some form fields. That
            # seems to happen in the old software if a user entered more characters
            # than the field definition actually allows. The extra character will
            # overflow in a new "field".
            # We can catch that by ensuring that we only accept known field names.
            # LATER: catching the error here is a bit annoying because it
            # basically means we're hard-coding all known field names which makes
            # it less convenient to work with.
            if unknown_fields:
                form_position = len(self.forms)
                msg = 'Form %d contains unknown field(s): %r' % (form_position, tuple(unknown_fields))
                raise ValueError(msg)
            return form
        if not self._load_delayed:
            form = form()
        return form

    def count(self):
        return self.form_batch_header.rec.form_count

    def __len__(self):
        return self.count()

    def __eq__(self, other):
        for attr in ('form_batch_header', 'forms'):
            if not hasattr(other, attr):
                return False
        return (self.form_batch_header == other.form_batch_header and
                self.forms == other.forms)

    def __ne__(self, other):
        return not(self == other)


class FormField(WithBinaryMeta):
    _struc = CDBFormat.field

    @property
    def name(self):
        return self.rec.name

    @property
    def value(self):
        return self.rec.corrected_result

    @value.setter
    def value(self, newval):
        self.update_rec(corrected_result=newval)

    # alias for field checking
    @property
    def corrected_result(self):
        return self.rec.corrected_result

    @property
    def recognizer_result(self):
        return self.rec.recognizer_result

    # hack to allow for mangling, see ascii.get_error_1
    @recognizer_result.setter
    def recognizer_result(self, newval):
        self.update_rec(recognizer_result=newval)

    @property
    def rejects(self):
        return self.rec.rejects

    # computation of rejects, see ascii.get_error_1
    @rejects.setter
    def rejects(self, newval):
        self.update_rec(rejects=newval)


class LazyDict(dict):
    ''' initializes the dict at the first key access '''
    # note: we don't need a defaultdict, the missing slot is sufficient

    def __new__(cls, func):
        return dict.__new__(cls)

    def __init__(self, func):
        self.func = func

    def __missing__(self, key):
        self.func(key)
        if key not in self:
            raise KeyError(key)
        return self[key]


class LazyList(list):
    ''' initialize list entries that are callable '''

    def __getitem__(self, idx):
        entry = super(LazyList, self).__getitem__(idx)
        if callable(entry):
            entry = entry()
            self[idx] = entry
        return entry


class Form(object):
    _field_record_size = FormField(None).record_size

    def __init__(self, parent, offset):
        self.record_size = 0
        self.parent = parent
        self.offset = offset
        self.form_header = None
        self.fields = None
        self._fields_loaded = False

        self._field_names = []
        self.field_offsets = []
        self.load_form_header()
        self.load_form_fields()

    @property
    def _load_delayed(self):
        return self.parent._load_delayed

    @property
    def field_names(self):
        # we need to trigger loading of the fields
        if not self._fields_loaded:
            self._do_load_form_fields()
        return self._field_names

    @property
    def batch_filename(self):
        return self.parent.batch_filename

    @property
    def filecontent(self):
        return self.parent.filecontent

    @property
    def pic_nr(self):
        warnings.warn('"cdb_tool.Form.pic_nr" is ambiguous, use "cdb_tool.Form.cdb_pic_nr" instead', DeprecationWarning)
        return self.cdb_pic_nr

    @property
    def cdb_pic_nr(self):
        return self.form_header.rec.imprint_line_short

    def load_form_header(self):
        self.form_header = FormHeader(self.filecontent, self.offset)
        self.record_size = self.form_header.record_size

    def load_form_fields(self):
        self.fields = LazyDict(self._do_load_form_fields)
        self._fields_loaded = False
        self.record_size = (self.form_header.record_size +
                            self._field_record_size
                            * self.form_header.rec.field_count)
        if self.offset + self.record_size > len(self.filecontent):
            raise ValueError('offset + record_size exceeds file size!\n'
                             'offset={} record_size={} file size={}'
                             .format(self.offset, self.record_size,
                                     len(self.filecontent)))
        if not self._load_delayed:
            self._do_load_form_fields()

    def is_dirty(self):
        for field in self.fields.values():
            if field.is_dirty():
                return True
        return False

    def is_deleted(self):
        return (self.cdb_pic_nr == 'DELETED')

    def _do_load_form_fields(self, key=None):
        # key could be used, but we need to create all fields in order
        if self._fields_loaded:
            return
        offset = self.offset + self.form_header.record_size
        for _ in range(self.form_header.rec.field_count):
            field = FormField(self.filecontent, offset)
            field_name = field.rec.name
            self.fields[field_name] = field
            self._field_names.append(field_name)
            self.field_offsets.append(offset - self.offset)
            offset += field.record_size
        self._fields_loaded = True

    def write_back(self):
        ''' write the form data and header back to file and update the structure '''
        buffer = self.filecontent
        written = False
        # for user editable fields, we check first and then write back.
        # Pass one: check if the encoding works
        for index, field_name in enumerate(self._field_names):
            field = self.fields[field_name]
            if field.edited_fields:
                try:
                    data = field._get_binary()
                except UnicodeError as e:
                    e.field = field
                    raise e
        # Pass Two: we are now safe to write
        for index, field_name in enumerate(self._field_names):
            field = self.fields[field_name]
            if field.edited_fields:
                data = field._get_binary()
                offset = self.field_offsets[index] + self.offset
                buffer[offset:offset + len(data)] = data
                field.edited_fields.clear()
                written = True

        if self.form_header.edited_fields:
            data = self.form_header._get_binary()
            offset = self.offset
            if not isinstance(buffer, bytes):
                # mmap'd file
                buffer[offset:offset + len(data)] = data
            else:
                # in testing "buffer" is a plain file-like object...
                new_buffer = buffer[:offset] + data + buffer[offset + len(data):]
                fp = self.parent.mmap_file
                fp.seek(0)
                fp.write(new_buffer)
                fp.seek(0)
            self.form_header.edited_fields.clear()
            written = True

        if written:
            self.parent.mmap_file.flush()

    def __getitem__(self, key):
        return self.fields[key]

    def __eq__(self, other):
        return (self.form_header == other.form_header and
                self.fields == other.fields)

    def __ne__(self, other):
        return not(self == other)

