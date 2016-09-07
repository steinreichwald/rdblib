# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from collections import namedtuple
import os
import sys

from ddc.lib.attribute_dict import AttrDict
from ddc.lib.result import Result


__all__ = [
    'guess_bunch_from_path',
    'guess_cdb_path',
    'guess_db_path',
    'guess_ibf_path',
    'guess_path',
    'ibf_subdir',
    'path_info_from_cdb',
    'path_info_from_db',
    'path_info_from_ibf',
    'DataBunch',
]

ibf_subdir = '00000001'

class DataBunch(namedtuple('DataBunch', 'cdb ibf db ask')):
    def is_complete(self):
        return (None not in self[:3])

    def is_processed(self):
        return self.ask is not None

    @classmethod
    def merge(cls, bunch, cdb=None, ibf=None, db=None, ask=None):
        cdb_ = cdb or bunch.cdb
        ibf_ = ibf or bunch.ibf
        db_ = db or bunch.db
        ask_ = ask or bunch.ask
        return DataBunch(cdb=cdb_, ibf=ibf_, db=db_, ask=ask_)


def path_info_from_cdb(cdb_path):
    if cdb_path is None:
        return (None, None)
    dirname = os.path.dirname(cdb_path)
    cdb_filename = os.path.basename(cdb_path)
    cdb_basename, extension = os.path.splitext(cdb_filename)
    return dirname, cdb_basename

def path_info_from_ibf(ibf_path):
    if ibf_path is None:
        return (None, None)
    img_dirname = os.path.dirname(ibf_path)
    if not img_dirname.endswith(ibf_subdir) and (img_dirname != ibf_subdir):
        raise ValueError('IBF not in default image dir')
    base_dirname = os.path.dirname(img_dirname)
    ibf_filename = os.path.basename(ibf_path)
    ibf_basename, extension = os.path.splitext(ibf_filename)
    return base_dirname, ibf_basename

def path_info_from_db(db_path):
    return path_info_from_cdb(db_path)

def path_info_from_ask(ask_path):
    return path_info_from_ibf(ask_path)

def guess_cdb_path(base_dir, basename):
    return os.path.join(base_dir, basename+'.CDB')

def guess_ibf_path(base_dir, basename):
    return os.path.join(base_dir, ibf_subdir, basename+'.IBF')

def guess_db_path(base_dir, basename):
    return os.path.join(base_dir, basename+'.db')

def guess_ask_path(base_dir, basename):
    return os.path.join(base_dir, ibf_subdir, basename+'.ask')

def _basedir_and_name_from_path(path):
    dot_extension = (os.path.splitext(path)[-1]).upper()
    cdb_path = path if (dot_extension in ('.CDB', '.RDB')) else None
    ibf_path = path if (dot_extension == '.IBF') else None
    db_path = path if (dot_extension == '.DB') else None
    ask_path = path if (dot_extension == '.ASK') else None
    if cdb_path is not None:
        base_dir, basename = path_info_from_cdb(cdb_path)
    elif ibf_path is not None:
        base_dir, basename = path_info_from_ibf(ibf_path)
    elif db_path is not None:
        base_dir, basename = path_info_from_db(db_path)
    elif ask_path is not None:
        base_dir, basename = path_info_from_ask(ask_path)
    else:
        raise ValueError('please specify at least one path')
    return Result((base_dir, basename), cdb_path=cdb_path, ibf_path=ibf_path, db_path=db_path, ask_path=ask_path)

def guess_bunch_from_path(path, file_casing_map):
    # <path> might be something like 'foo/../foo' which messes up with filename
    # lookup in the file_casing_map (as discoverlib normalizes paths - which is
    # good). So let's normalize the input path outself.
    normalized_path = os.path.abspath(os.path.normpath(path))
    result = _basedir_and_name_from_path(normalized_path)
    (base_dir, basename) = result.value
    r = AttrDict(result.data)
    if r.cdb_path is None:
        r.cdb_path = file_casing_map.get(guess_cdb_path(base_dir, basename).lower())
    if r.ibf_path is None:
        r.ibf_path = file_casing_map.get(guess_ibf_path(base_dir, basename).lower())
    if r.db_path is None:
        r.db_path = file_casing_map.get(guess_db_path(base_dir, basename).lower())
    if r.ask_path is None:
        r.ask_path = file_casing_map.get(guess_ask_path(base_dir, basename).lower())
    return DataBunch(cdb=r.cdb_path, ibf=r.ibf_path, db=r.db_path, ask=r.ask_path)

def guess_path(input_, type_):
    is_fp_like = hasattr(input_, 'close')
    input_path = input_ if (not is_fp_like) else input_.name
    (base_dir, basename) = _basedir_and_name_from_path(input_path).value
    guess_func_name = ('guess_%s_path' % type_)
    module = sys.modules[__name__]
    guess_func = getattr(module, guess_func_name)
    return guess_func(base_dir, basename)

