# -*- coding: utf-8 -*-

import os
import sys

from ..cdb import open_cdb, BatchHeader, Field, FormHeader, CDB_ENCODING
from ..mmap_file import MMapFile


__all__ = ['find_broken_form_main']

try:
    from ddc.client.config import ALL_FIELD_NAMES
except ImportError:
    ALL_FIELD_NAMES = None


def calculate_position_of_form_in_cdb(form_index, nr_fields_per_form):
    bytes_batch_header = BatchHeader.size
    bytes_per_field = Field.size
    bytes_per_form = FormHeader.size + (nr_fields_per_form * bytes_per_field)
    return bytes_batch_header + (form_index * bytes_per_form)

def repair_form(cdb_path, form_index, field_index, *, field_names):
    nr_fields_per_form = len(field_names)
    form_byte_positon = calculate_position_of_form_in_cdb(form_index, nr_fields_per_form=nr_fields_per_form)
    bytes_per_field = Field.size
    cdb_bytes = MMapFile(cdb_path, access='write')

    field_position = form_byte_positon + FormHeader.size + field_index * bytes_per_field
    field_bytes = cdb_bytes[field_position:field_position+bytes_per_field]
    field_data = Field.parse(field_bytes)

    correct_field_name = field_names[field_index]
    form_nr = form_index + 1
    field_nr = field_index + 1
    print('fixing overwritten field name %r (field #%d) in form #%d' % (correct_field_name, field_nr, form_nr))
    b_correct_field_name = correct_field_name.encode(CDB_ENCODING)
    missing_bytes = 20 - len(b_correct_field_name)
    b_name_value = b_correct_field_name + (missing_bytes * b'\x00')
    # if there is an invalid field name also "number" + "status" were overwritten
    field_data['number'] = field_nr
    field_data['status'] = 1
    field_data['name'] = b_name_value
    fixed_field_bytes = Field.to_bytes(field_data)

    cdb_bytes[field_position:field_position+bytes_per_field] = fixed_field_bytes
    cdb_bytes.flush()
    cdb_bytes.close()


def check_for_broken_form(cdb_path, field_names=None, try_repair=False):
    result = open_cdb(cdb_path, field_names=field_names, access='read')
    if result == False:
        can_repair_error = (result.form_index is not None) and (result.key == 'form.unknown_fields')
        if try_repair and can_repair_error:
            repair_form(cdb_path, result.form_index, result.field_index, field_names=field_names)
        else:
            print(result.message)
    if getattr(result, 'warnings'):
        for warning in result.warnings:
            print(warning)
    if result == True:
        result.cdb_fp.close()
    return


def find_broken_form_main():
    if len(sys.argv) < 2:
        sys.stderr.write('usage: %r [--try-repair] CDB\n' % sys.argv[0])
        sys.exit(1)
    try_repair = (len(sys.argv) >= 3) and ('--try-repair' in sys.argv)
    cdb_index = 2 if try_repair else 1
    cdb_path = os.path.abspath(sys.argv[cdb_index])
    if not os.path.isfile(cdb_path):
        sys.stderr.write('no such file "%s"\n' % sys.argv[1])
        sys.exit(2)
    check_for_broken_form(cdb_path, field_names=ALL_FIELD_NAMES, try_repair=try_repair)

