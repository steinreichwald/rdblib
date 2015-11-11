# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from collections import namedtuple
import os
import sys

from ddc.lib.attribute_dict import AttrDict
from ddc.lib.result import Result
from .filesystem_utils import look_for_file


__all__ = [
    'guess_bunch_from_path',
    'guess_cdb_path',
    'guess_durus_path',
    'guess_ibf_path',
    'guess_path',
    'path_info_from_cdb',
    'path_info_from_ibf',
    'path_info_from_durus',
    'DataBunch',
]

class DataBunch(namedtuple('DataBunch', 'cdb ibf durus ask')):

    def is_complete(self):
        return (None not in self[:3])

    def is_processed(self):
        return self.ask is not None

ibf_subdir = '00000001'

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

def path_info_from_durus(durus_path):
    return path_info_from_cdb(durus_path)

def path_info_from_ask(ask_path):
    return path_info_from_ibf(ask_path)

def guess_cdb_path(base_dir, basename):
    return os.path.join(base_dir, basename+'.cdb')

def guess_ibf_path(base_dir, basename):
    return os.path.join(base_dir, ibf_subdir, basename+'.ibf')

def guess_durus_path(base_dir, basename):
    return os.path.join(base_dir, basename+'.durus')

def guess_ask_path(base_dir, basename):
    return os.path.join(base_dir, ibf_subdir, basename+'.ask')

def _basedir_and_name_from_path(path):
    dot_extension = (os.path.splitext(path)[-1]).lower()
    cdb_path = path if (dot_extension == '.cdb') else None
    ibf_path = path if (dot_extension == '.ibf') else None
    durus_path = path if (dot_extension == '.durus') else None
    ask_path = path if (dot_extension == '.ask') else None
    if cdb_path is not None:
        base_dir, basename = path_info_from_cdb(cdb_path)
    elif ibf_path is not None:
        base_dir, basename = path_info_from_ibf(ibf_path)
    elif durus_path is not None:
        base_dir, basename = path_info_from_durus(durus_path)
    elif ask_path is not None:
        base_dir, basename = path_info_from_ask(ask_path)
    else:
        raise ValueError('please specify at least one path')
    return Result((base_dir, basename), cdb_path=cdb_path, ibf_path=ibf_path, durus_path=durus_path, ask_path=ask_path)

def guess_bunch_from_path(path, file_casing_map):
    result = _basedir_and_name_from_path(path)
    (base_dir, basename) = result.value
    r = AttrDict(result.data)
    if r.cdb_path is None:
        r.cdb_path = file_casing_map.get(guess_cdb_path(base_dir, basename).lower())
    if r.ibf_path is None:
        r.ibf_path = file_casing_map.get(guess_ibf_path(base_dir, basename).lower())
    if r.durus_path is None:
        r.durus_path = file_casing_map.get(guess_durus_path(base_dir, basename).lower())
    if r.ask_path is None:
        r.ask_path = file_casing_map.get(guess_ask_path(base_dir, basename).lower())
    return DataBunch(cdb=r.cdb_path, ibf=r.ibf_path, durus=r.durus_path, ask=r.ask_path)

def guess_path(input_, type_):
    is_fp_like = hasattr(input_, 'close')
    input_path = input_ if (not is_fp_like) else input_.name
    (base_dir, basename) = _basedir_and_name_from_path(input_path).value
    guess_func_name = ('guess_%s_path' % type_)
    module = sys.modules[__name__]
    guess_func = getattr(module, guess_func_name)
    return guess_func(base_dir, basename)

# ----------------------------------------------------------------------------
# all functionality below should be considered deprecated.
# Please use DiscoverLib + BunchAssembler instead.

def cdb_path(cdb_dir, cdb_basename):
    # use look_for_file to check for unique .cdb names, too
    return look_for_file(cdb_dir, cdb_basename, 'cdb')

def ibf_path(cdb_dir, cdb_basename):
    ibf_dir = os.path.join(cdb_dir, ibf_subdir)
    return look_for_file(ibf_dir, cdb_basename, 'ibf')

def durus_path(cdb_dir, cdb_basename):
    return look_for_file(cdb_dir, cdb_basename, 'durus')

def ask_path(cdb_dir, cdb_basename):
    ask_dir = os.path.join(cdb_dir, ibf_subdir)
    return look_for_file(ask_dir, cdb_basename, 'ask')

def databunch_for_durus(some_file_path):
    '''
    this is a simplified and more general version of databunch_for_cdb
    for the current needs of the GUI.
    '''
    dirpath = os.path.dirname(some_file_path)
    durus_filename = os.path.basename(some_file_path)
    file_basename = os.path.splitext(durus_filename)[0]
    cdb_filepath = cdb_path(dirpath, file_basename)
    ibf_filepath = ibf_path(dirpath, file_basename)
    durus_filepath = durus_path(dirpath, file_basename)
    ask_filepath = ibf_path(dirpath, file_basename)
    data = DataBunch(
        cdb=cdb_filepath,
        ibf=ibf_filepath,
        durus=durus_filepath,
        ask=ask_filepath,
    )
    return data

