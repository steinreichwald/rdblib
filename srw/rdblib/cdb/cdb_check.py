# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from io import BytesIO
import os
import re

import bitmath
from schwarz.log_utils import l_

from ..lib.filesize import format_filesize
from ..lib.result import Result
from ..mmap_file import MMapFile
from ..utils import filecontent
from .cdb_format import BatchHeader, Field, FormHeader, CDB_ENCODING


__all__ = ['open_cdb']

MAX_RDB_SIZE = bitmath.MiB(100)
# in production most RDB files have 61 fields
DEFAULT_NUMBER_FIELDS = 61
re_fieldname = re.compile('^[A-Za-z\-_0-9]+$')

def open_cdb(cdb_path, *, field_names=None, required_fields=None, access='write', log=None, ignore_size=False):
    log = l_(log)
    warnings = []
    is_pathlike = isinstance(cdb_path, (str, os.PathLike))
    if is_pathlike:
        filesize = bitmath.Byte(os.stat(cdb_path).st_size)
        filesize_str = format_filesize(filesize, locale='de')
        if filesize >= MAX_RDB_SIZE and (not ignore_size):
            return _error('Die CDB-Datei ist defekt (%s groß)' % filesize_str, warnings=warnings, key='file.too_big')

        try:
            cdb_fp = MMapFile(cdb_path, access=access, log=log)
        except OSError:
            return _error('Die CDB-Datei ist vermutlich noch in Bearbeitung.', warnings=warnings, key='file.is_locked')

        max_size = -1
        if ignore_size:
            max_size = BatchHeader.size + 300 * calculate_bytes_per_form(DEFAULT_NUMBER_FIELDS)
        cdb_bytes = filecontent(cdb_fp, size=max_size)
    else:
        cdb_fp = cdb_path
        previous_pos = cdb_fp.tell()
        cdb_bytes = cdb_fp.read()
        cdb_fp.seek(previous_pos)

    cdb_data = BytesIO(cdb_bytes)
    filesize = len(cdb_bytes)
    min_bytes = BatchHeader.size + FormHeader.size + Field.size
    if filesize < min_bytes:
        min_size_str = format_filesize(min_bytes, locale='de')
        msg = 'Die CDB-Datei ist zu klein: %s, mindestens %s erwartet' % (min_size_str, filesize_str)
        cdb_fp.close()
        return _error(msg, warnings=warnings, key='file.too_small')

    header_data = cdb_data.read(BatchHeader.size)
    assert len(header_data) == BatchHeader.size
    batch_header = BatchHeader.parse(header_data)
    form_count = batch_header['form_count']
    if form_count < 1:
        msg = 'CDB enthält laut Header keine Belege (form_count=%d)' % form_count
        cdb_fp.close()
        return _error(msg, warnings=warnings, key='file.no_records')

    expected_size = BatchHeader.size + form_count * calculate_bytes_per_form(DEFAULT_NUMBER_FIELDS)
    if ignore_size and (form_count < 300):
        # This is helpful if the actual file is huge, is cut to 300 forms but
        # the batch header contains a lower form count.
        # The code already read some bytes before to parse the batch header.
        cdb_data.seek(0)
        cdb_bytes = cdb_data.read(expected_size)
        filesize = len(cdb_bytes)
        assert (filesize == expected_size), f'{filesize} (CDB size) != {expected_size} (expected size)'
        cdb_data = BytesIO(cdb_bytes)
        # seeking to the form header so the following parsing code works
        cdb_data.seek(BatchHeader.size)

    if field_names:
        field_count = len(field_names)
    else:
        estimated_bytes_per_form = (filesize - BatchHeader.size) // form_count
        field_count = (estimated_bytes_per_form - FormHeader.size) // Field.size
    bytes_per_form = calculate_bytes_per_form(field_count)

    expected_file_size = BatchHeader.size + (form_count * bytes_per_form)
    extra_bytes = filesize - expected_file_size
    if expected_file_size != filesize:
        msg = 'Die CDB hat eine ungewöhnliche Größe (mindestens %d Bytes zu viel bei %d Belegen laut Header)' % (extra_bytes, form_count)
        cdb_fp.close()
        return _error(msg, warnings=warnings, key='file.junk_after_last_record')

    expected_fields_per_form = (bytes_per_form - FormHeader.size) // Field.size
    if expected_fields_per_form < 1:
        msg = 'Die CDB ist zu klein (%d Belege laut Header)' % form_count
        cdb_fp.close()
        return _error(msg, warnings=warnings, key='file.too_small')

    if field_names is None:
        result = gather_field_names(cdb_data, expected_fields_per_form, warnings=warnings, filesize=filesize, form_count=form_count)
        if not result:
            cdb_fp.close()
            return result
        field_names = result.field_names
        field_count = len(field_names)
        bytes_per_form = calculate_bytes_per_form(field_count)
    if required_fields is not None:
        missing_set = set(required_fields).difference(field_names)
        if missing_set:
            missing_fields = tuple(sorted(missing_set))
            msg = 'Fehlende Felder in Formular #1: %s' % ', '.join(missing_fields)
            cdb_fp.close()
            return _error(msg, warnings=warnings, key='form.missing_field', form_index=0)

    encode_ = lambda s: s.encode(CDB_ENCODING)
    b_field_names = tuple(map(encode_, field_names))
    calculated_form_count = (filesize - BatchHeader.size) // bytes_per_form
    expected_file_size = calculate_filesize(calculated_form_count, field_count)
    extra_bytes = filesize - expected_file_size
    if form_count != calculated_form_count:
        msg = u'Die Datei enthält %d Belege (Header), es müssten %d Belege vorhanden sein (Dateigröße): %s Bytes zu viel'
        msg_text = msg % (form_count, calculated_form_count, extra_bytes)
        cdb_fp.close()
        return _error(msg_text, warnings=warnings, key='file.size_does_not_match_records')
    if extra_bytes:
        msg = 'Die CDB hat eine ungewöhnliche Größe (%d Bytes zu viel bei %d Belegen)'
        return _error(msg % (extra_bytes, calculated_form_count), warnings=warnings, key='file.junk_after_last_record')

    next_index = 0
    while True:
        current_index = next_index
        form_nr = current_index + 1
        next_index += 1
        header_data = cdb_data.read(FormHeader.size)
        if len(header_data) == 0:
            break
        assert len(header_data) == FormHeader.size
        form_header = FormHeader.parse(header_data)
        h_field_count = form_header['field_count']
        if h_field_count != field_count:
            msg = 'Formular #%d ist vermutlich fehlerhaft (%d Felder statt %d)' % (form_nr, h_field_count, field_count)
            cdb_fp.close()
            return _error(msg, warnings=warnings, key='form.unusual_number_of_fields', form_index=current_index)

        unknown_names = []
        seen_names = []
        index_of_bad_field = None
        for i in range(h_field_count):
            field_data = cdb_data.read(Field.size)
            assert len(field_data) == Field.size
            field = Field.parse(field_data)
            b_field_name = field['name'].rstrip(b'\x00')
            if b_field_name not in b_field_names:
                unknown_names.append(b_field_name)
                if index_of_bad_field is None:
                    index_of_bad_field = i
            else:
                seen_names.append(b_field_name)
        unseen_names = set(b_field_names).difference(set(seen_names))
        if unknown_names:
            unknown_msg = 'unbekanntes Feld %r' % (b', '.join(unknown_names))
            unseen_msg = 'fehlendes Feld %r' % (b', '.join(unseen_names))
            msg = 'Formular #%d ist vermutlich fehlerhaft (%s, %s).' % (form_nr, unknown_msg, unseen_msg)
            cdb_fp.close()
            return _error(
                msg,
                warnings=warnings,
                key='form.unknown_fields',
                form_index=current_index,
                field_index=index_of_bad_field
            )

        # CDB/RDB files might contain empty an PIC field in case of OCR problems.
        # We can apply workarounds for that but it might help finding the bad
        # form.
        cdb_pic = form_header['imprint_line_short'].rstrip(b'\x00')
        if cdb_pic == b'':
            msg = 'Formular #%d ist wahrscheinlich fehlerhaft (keine PIC-Nr vorhanden)' % form_nr
            warnings.append(msg)

    return Result(True, cdb_fp=cdb_fp, warnings=warnings, key=None, form_index=None, field_index=None)

def calculate_bytes_per_form(nr_fields):
    return (nr_fields * Field.size) + FormHeader.size

def calculate_filesize(nr_forms, nr_fields):
    return nr_forms * calculate_bytes_per_form(nr_fields) + BatchHeader.size

def gather_field_names(cdb_data, expected_nr, *, warnings=(), filesize=None, form_count=None):
    offset = cdb_data.tell()
    form_index = 0
    form_nr = form_index + 1
    header_data = cdb_data.read(FormHeader.size)
    assert len(header_data) == FormHeader.size
    form_header = FormHeader.parse(header_data)
    field_count = form_header['field_count']
    if field_count != expected_nr:
        extra_bytes_msg = ''
        if filesize and form_count:
            extra_bytes = filesize - calculate_filesize(form_count, field_count)
            extra_bytes_msg = ' (oder %d extra Bytes?)' % extra_bytes
        msg = 'Formular #%d enthält %d Felder, erwartet wurden aber %d%s.' % (form_nr, field_count, expected_nr, extra_bytes_msg)
        return _error(msg, warnings=warnings, key='form.unusual_number_of_fields', form_index=form_index)

    field_names = []
    for i in range(field_count):
        field_data = cdb_data.read(Field.size)
        assert len(field_data) == Field.size
        field = Field.parse(field_data)
        b_field_name = field['name'].rstrip(b'\x00')
        if not is_plausible_field_name(b_field_name):
            msg = 'Formular #%d enthält ungültiges Feld "%r"' % (form_nr, b_field_name)
            return _error(msg, key='form.bad_field_name', form_index=form_index)
        field_name = b_field_name.decode(CDB_ENCODING)
        field_names.append(field_name)
    cdb_data.seek(offset)
    return Result(True, field_names=field_names)


def is_plausible_field_name(b_name):
    try:
        name = b_name.decode(CDB_ENCODING)
    except UnicodeDecodeError:
        return False
    if not re_fieldname.search(name):
        return False
    return True


def _error(msg, warnings=(), form_index=None, field_index=None, *, key):
    return Result(False,
        cdb_fp=None,
        message=msg,
        warnings=warnings,
        key=key,
        form_index=form_index,
        field_index=field_index,
    )
