#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

"""
classes for dealing with prescription-files
"""

import io
import sys
import mmap
import os.path
from struct import pack, unpack_from, calcsize
from collections import namedtuple

from ddc.tool.meta import BinaryMeta
from ddc.compat import with_metaclass
from ddc.dbdef import cdb_definition


########################################################################
class MMapFile(mmap.mmap):
    """
    memory-like file, based on mmap.
    The file does intentionally not support the standard file interface but
    only the methods that make sense for our purpose.
    """

    #----------------------------------------------------------------------
    def __new__(cls, filename):
        """Constructor"""
        
        with io.open(filename, 'r+b') as f:
            self = super(MMapFile, cls).__new__(cls, f.fileno(), 0)  
        self.name = filename
        self.closed = False
        return self
    
    if sys.platform == 'win32':
        # windows will return 0 if an error occured. Linux/Mac raise an error.
        def flush(self, *args, **kw):
            ret = super(MMapFile, self).flush(*args, **kw)
            if ret == 0:
                raise WindowsError('something went wrong in flush().')
            return ret
    
    def close(self):
        super(MMapFile, self).close()
        self.closed = True
    
    def __getattribute__(self, name):
        if name in ('__dict__', '__members__', '__methods__', '__class__',
                    'flush', 'close', 'closed', 'name'):
            return super(MMapFile, self).__getattribute__(name)
        raise AttributeError("type object '{}' has no attribute '{}'"
                             .format(self.__class__.__name__, name))


class WithBinaryMeta(with_metaclass(BinaryMeta)):
    ''' helper class for python 2/3 compatibility '''

    _encoding = cdb_definition.encoding


class FormBatchHeader(WithBinaryMeta):
    _struc = cdb_definition.Form_Defn.batchheader_struc


class FormHeader(WithBinaryMeta):
    _struc = cdb_definition.Form_Defn.header_struc


class FormBatch(object):

    def __init__(self, batch_filename, delay_load=False):
        self.mmap_file = MMapFile(batch_filename)
        self.batch_filecontent = self.mmap_file

        self.load_form_batch_header()
        self._load_delayed = delay_load
        self.load_forms()

    def close(self):
        self.mmap_file.close()

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
        self.form_batch_header = FormBatchHeader(
            self.batch_filecontent)

    def load_forms(self):
        self.forms = []
        offset = self.form_batch_header.record_size
        len_job_filecontent = len(self.batch_filecontent)
        while offset < len_job_filecontent:
            prescription = Form(self, offset)
            self.forms.append(prescription)
            offset += prescription.record_size
            if len(self.forms) > len(self):
                raise ValueError('prescription count exceeds header info')
        if len(self.forms) != len(self):
            raise ValueError("read prescription count differs from header info")

    @property
    def _image_filename(self):
        """
        The intention of the original format of the RDB-files is to
        get the IBF-Filename with the following code:

            return self.prescription_job_header.ibf_format_string % \
                   self.prescription_job_header.ibf_path

        Doing this it's not possible to move the files (especially the IBF-file)
        to another location (for testing or backup), because the basepath to
        the IBF-file is aboslute and hard coded in the RDB-file.

        In real life the IBF-file always resides in a subdirectory with the name
        "00000001" below the RDB-file, that's why we can safely calculate the
        path to the IBF-file from the path to the RDB-file.
        """
        pathname, filename = os.path.split(self.batch_filename)
        filename, _ = os.path.splitext(filename)
        return os.path.join(pathname, '00000001', '%s.IBF' % filename)

    def count(self):
        return self.form_batch_header.rec.form_count

    def __len__(self):
        return self.count()

    def __eq__(self, other):
        return (self.form_batch_header == other.form_batch_header and
                self.forms == other.forms)

    def __ne__(self, other):
        return not(self == other)

    def __hash__(self):
        return super(FormBatch, self).__hash__()


class FormField(WithBinaryMeta):
    _struc = cdb_definition.Form_Defn.field_struc

    @property
    def name(self):
        return self.rec.name

    @property
    def value(self):
        return self.rec.corrected_result

    @value.setter
    def value(self, newval):
        self.update_rec(corrected_result=newval)

    @property
    def valid(self):
        return self.rec.valid


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


class Form(object):
    _field_record_size = FormField(None).record_size

    def __init__(self, parent, offset):
        self.record_size = 0
        self.parent = parent
        self.offset = offset

        self.load_form_header()
        self.load_form_fields()
        self.is_dirty = False

    @property
    def _load_delayed(self):
        return self.parent._load_delayed

    @property
    def batch_filename(self):
        return self.parent.batch_filename

    @property
    def batch_filecontent(self):
        return self.parent.batch_filecontent

    def load_form_header(self):
        self.form_header = FormHeader(self.batch_filecontent, self.offset)
        self.record_size = self.form_header.record_size

    def load_form_fields(self):
        self.fields = LazyDict(self._do_load_form_fields)
        self._fields_loaded = False
        self.record_size = (self.form_header.record_size +
                            self._field_record_size
                            * self.form_header.rec.field_count)
        if self.offset + self.record_size > len(self.batch_filecontent):
            raise ValueError('offset + record_size exceeds file size!\n'
                             'offset={} record_size={} file size={}'
                             .format(self.offset, self.record_size,
                                     len(self.batch_filecontent)))
        if not self._load_delayed:
            self._do_load_form_fields()

    def _do_load_form_fields(self, key=None):
        # key could be used, but we need to create all fields in order
        if self._fields_loaded:
            return
        self.field_names = []
        self.field_offsets = []
        offset = self.offset + self.form_header.record_size
        # nota bene: range can break the machine when random data is read
        for _ in xrange(self.form_header.rec.field_count):
            field = FormField(self.batch_filecontent, offset)
            field_name = field.rec.name
            self.fields[field_name] = field
            self.field_names.append(field_name)
            self.field_offsets.append(offset - self.offset)
            offset += field.record_size
        self._fields_loaded = True

    def write_back(self):
        ''' write the form data back to file and update the structure '''
        buffer = self.batch_filecontent
        for index, field_name in enumerate(self.field_names):
            field = self.fields[field_name]
            if field.edited_fields:
                data = field._get_binary()
                offset = self.field_offsets[index] + self.offset
                buffer[offset:offset + len(data)] = data
                field.edited_fields.clear()
        self.parent.mmap_file.flush()

    def __getitem__(self, key):
        return self.fields[key]

    def __eq__(self, other):
        return (self.form_header == other.form_header and
                self.fields == other.fields)

    def __ne__(self, other):
        return not(self == other)

    def __hash__(self):
        return super(Form, self).__hash__()

    @property
    def pic_nr(self):
        return self.form_header.rec.imprint_line_short


class FormImageBatchHeader(WithBinaryMeta):
    _struc = cdb_definition.Image_Defn.header_struc


class FormImageBatchIndexEntry(WithBinaryMeta):
    _struc = cdb_definition.Image_Defn.index_struc


class FormImageBatch(object):

    def __init__(self, image_job_filename):
        self.image_job_filename = image_job_filename

        with io.open(image_job_filename, 'rb', buffering=5000000) as image_file:
            self.filecontent = image_file.read()

        self.load_header()
        self.load_directories()

    def close(self):
        pass # XXX

    def load_header(self):
        self.header = FormImageBatchHeader(self.filecontent)

    def load_directories(self):
        offset = self.header.rec.offset_first_index
        self.image_entries = []
        while offset != 0:
            directory = FormImageBatchIndexDirectory(self.filecontent, offset)
            for entry in directory:
                self.image_entries.append(entry)
            offset = directory.offset_next_index
        self.build_codnr_index()

    def build_codnr_index(self):
        self.codnr_index = {}
        for entry in self.image_entries:
            self.codnr_index[entry.rec.codnr] = entry

    def get_tiff_image_4_codnr(self, codnr):
        if codnr in self.codnr_index:
            entry = self.codnr_index[codnr]
            return self.tiff_data_4_entry(entry)
        else:
            return None

    def get_tiff_image_4_nr(self, index):
        entry = self.image_entries[index]
        return self.tiff_data_4_entry(entry)

    def tiff_data_4_entry(self, entry):
        return self.filecontent[entry.rec.image_offset:
                                entry.rec.image_offset+entry.rec.image_size]

    def image_count(self):
        return len(self.image_entries)


class FormImageBatchIndexDirectory(object):

    def __init__(self, filecontent, offset):
        self.entries = []

        image_count = -1
        while image_count != 0:
            entry = FormImageBatchIndexEntry(filecontent, offset)
            self.entries.append(entry)
            if image_count == -1:
                self.offset_next_index = entry.rec.offset_next_index
                image_count = entry.rec.indexblock_len
            image_count -= 1
            offset += len(entry)

    def __iter__(self):
        return iter(self.entries)
