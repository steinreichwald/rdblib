# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from io import BytesIO
import os

from ddc.lib.filesize import format_filesize
from ddc.lib.log_proxy import l_
from ddc.lib.result import Result
from ..mmap_file import MMapFile
from ..utils import filecontent
from .cdb_format import BatchHeader, Field, FormHeader, CDB_ENCODING


__all__ = ['open_cdb']

_100mb = 100 * 1024 * 1024

def open_cdb(cdb_path, *, field_names, access='write', log=None):
    log = l_(log)
    filesize = os.stat(cdb_path).st_size
    warnings = []
    if filesize >= _100mb:
        size_str = format_filesize(filesize, locale='de')
        return _error('Die CDB-Datei ist defekt (%s groß)' % size_str, warnings=warnings)

    encode_ = lambda s: s.encode(CDB_ENCODING)
    b_field_names = tuple(map(encode_, field_names))
    nr_fields_per_form = len(b_field_names)
    bytes_batch_header = BatchHeader.size
    bytes_per_field = Field.size
    bytes_per_form = FormHeader.size + (nr_fields_per_form * bytes_per_field)
    calculated_form_count = (filesize - bytes_batch_header) // bytes_per_form
    expected_file_size = bytes_batch_header + (calculated_form_count * bytes_per_form)
    if expected_file_size != filesize:
        extra_bytes = filesize - expected_file_size
        msg = 'Die CDB hat eine ungewöhnliche Größe (%d Bytes zu viel bei %d Belegen)'
        return _error(msg % (extra_bytes, calculated_form_count), warnings=warnings)

    try:
        cdb_fp = MMapFile(cdb_path, access=access, log=log)
    except OSError:
        return _error('Die CDB-Datei ist vermutlich noch in Bearbeitung.', warnings=warnings)

    cdb_data = BytesIO(filecontent(cdb_fp))
    header_data = cdb_data.read(bytes_batch_header)
    assert len(header_data) == BatchHeader.size
    batch_header = BatchHeader.parse(header_data)
    form_count = batch_header['form_count']
    expected_file_size = bytes_batch_header + (form_count * bytes_per_form)
    if expected_file_size != filesize:
        extra_bytes = filesize - expected_file_size
        msg = u'Die Datei enthält %d Belege (Header), es müssten %d Belege vorhanden sein (Dateigröße).'
        return _error(msg % (form_count, calculated_form_count), warnings=warnings)

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
        field_count = form_header['field_count']
        if field_count != nr_fields_per_form:
            msg = 'Formular #%d ist vermutlich fehlerhaft (%d Felder statt %d)' % (form_nr, field_count, nr_fields_per_form)
            return _error(msg, warnings=warnings)

        unknown_names = []
        seen_names = []
        for i in range(field_count):
            field_data = cdb_data.read(bytes_per_field)
            assert len(field_data) == bytes_per_field
            field = Field.parse(field_data)
            b_field_name = field['name'].rstrip(b'\x00')
            if b_field_name not in b_field_names:
                unknown_names.append(b_field_name)
            else:
                seen_names.append(b_field_name)
        unseen_names = set(b_field_names).difference(set(seen_names))
        if unknown_names:
            unknown_msg = 'unbekanntes Feld %r' % (b', '.join(unknown_names))
            unseen_msg = 'fehlendes Feld %r' % (b', '.join(unseen_names))
            msg = 'Formular #%d ist vermutlich fehlerhaft (%s, %s).' % (form_nr, unknown_msg, unseen_msg)
            return _error(msg, warnings=warnings)

        # CDB/RDB files might contain empty an PIC field in case of OCR problems.
        # We can apply workarounds for that but it might help finding the bad
        # form.
        cdb_pic = form_header['imprint_line_short'].rstrip(b'\x00')
        if cdb_pic == b'':
            msg = 'Formular #%d ist wahrscheinlich fehlerhaft (keine PIC-Nr vorhanden)' % form_nr
            warnings.append(msg)

    return Result(True, cdb_fp=cdb_fp, warnings=warnings)

def _error(msg, warnings=()):
    return Result(False, cdb_fp=None, message=msg, warnings=warnings)
