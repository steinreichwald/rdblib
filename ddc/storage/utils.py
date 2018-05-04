# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import mmap
import os

from ddc.lib import l_
from ddc.lib.attribute_dict import AttrDict
from .paths import get_path_from_instance


__all__ = ['create_backup', 'filecontent', 'DELETE']

class DELETE(object):
    pass

def filecontent(mmap_or_filelike):
    if isinstance(mmap_or_filelike, mmap.mmap):
        return mmap_or_filelike
    fp = mmap_or_filelike
    old_pos = fp.tell()
    fp.seek(0)
    content = fp.read()
    fp.seek(old_pos)
    return content

def _as_filelike(source):
    if isinstance(source, str):
        return open(source, 'rb')
    elif hasattr(source, 'filecontent'):  # FormBatch
        return AttrDict({
            'name': get_path_from_instance(source.mmap_file),
            'read': lambda: source.filecontent,
        })
    return source

def create_backup(source, backup_dir, *, log=None, ignore_errors=False):
    log = l_(log)
    try:
        source_fp = _as_filelike(source)
    except (FileNotFoundError, PermissionError) as e:
        log.error('unable to open file %s: %s', source, e)
        if ignore_errors:
            return None
        raise

    file_data = source_fp.read()
    previous_path = source_fp.name
    base_path, previous_extension = os.path.splitext(previous_path)
    basename = os.path.basename(base_path)
    try:
        os.makedirs(backup_dir, exist_ok=True)
    except (FileNotFoundError, PermissionError) as e:
        log.error('unable to create backup directory %s: %s', backup_dir, e)
        if ignore_errors:
            return None
        raise

    ext_nr = 0
    # Adding .BAK to the filename ensures the backup file can not be
    # opened accidentally by users.
    extension = previous_extension + '.BAK'
    while True:
        backup_path = os.path.join(backup_dir, basename+extension)
        try:
            # mode "xb" (Python 3.3+) ensures we never overwrite an
            # existing backup file
            with open(backup_path, 'xb') as fp:
                fp.write(file_data)
            log.debug('created backup in %s', backup_path)
            break
        except FileExistsError:
            log.debug('file %s already exists, must try another backup filename', os.path.basename(backup_path))
            ext_nr += 1
            extension = previous_extension + '.BAK' + '.' + str(ext_nr)
        except PermissionError as e:
            # This likely means we are not allowed to create any file in this
            # directory, leading to an endless loop so we should abort here.
            log.error('unable to create backup file %s: %s', backup_path, e)
            if ignore_errors:
                return None
            raise
    return backup_path

