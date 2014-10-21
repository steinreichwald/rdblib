# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from collections import namedtuple
import os

from .filesystem_utils import look_for_file


__all__ = ['databunch_for_cdb', 'expected_durus_path', 'DataBunch']

class DataBunch(namedtuple('DataBunch', 'cdb ibf durus')):
    def __init__(self, cdb=None, ibf=None, durus=None):
        super(DataBunch, self).__init__(cdb=cdb, ibf=ibf, durus=durus)

    def is_complete(self):
        return (None not in self)


def cdb_path(cdb_dir, cdb_basename):
    # use look_for_file to check for unique .cdb names, too
    return look_for_file(cdb_dir, cdb_basename, 'cdb')

def durus_path(cdb_dir, cdb_basename):
    return look_for_file(cdb_dir, cdb_basename, 'durus')

def ibf_path(cdb_dir, cdb_basename):
    ibf_dir = os.path.join(cdb_dir, '00000001')
    return look_for_file(ibf_dir, cdb_basename, 'ibf')

def databunch_for_cdb(cdb_path, add_missing_durus_path=False):
    dirpath = os.path.dirname(cdb_path)
    cdb_filename = os.path.basename(cdb_path)
    file_basename = os.path.splitext(cdb_filename)[0]
    durus_filepath = durus_path(dirpath, file_basename)
    if (durus_filepath is None) and add_missing_durus_path:
        durus_filepath = expected_durus_path(cdb_path)
    data = DataBunch(
        cdb=cdb_path,
        ibf=ibf_path(dirpath, file_basename),
        durus=durus_filepath,
    )
    return data

def expected_durus_path(cdb_path):
    basename, extension = os.path.splitext(cdb_path)
    return basename + '.durus'

def databunch_for_durus(some_file_path):
    '''
    this is a simplified and more general version of databunch_for_cdb that
    works better for the GUI.

    XXX we should provide a default behavior that checks for RDB/CDB and
    provides the right default behavior
    '''
    dirpath = os.path.dirname(some_file_path)
    durus_filename = os.path.basename(some_file_path)
    file_basename = os.path.splitext(durus_filename)[0]
    durus_filepath = durus_path(dirpath, file_basename)
    cdb_filepath = cdb_path(dirpath, file_basename)
    ibf_filepath = ibf_path(dirpath, file_basename)
    data = DataBunch(
        cdb=cdb_filepath,
        ibf=ibf_filepath,
        durus=durus_filepath,
    )
    return data

