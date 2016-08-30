# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from io import BytesIO
import logging

from ddc.lib.attribute_dict import AttrDict
from .batch import Batch
from .cdb import CDBFile, CDBForm
from ddc.storage.durus_ import create_durus_fixture
from ddc.storage.ibf import create_ibf
from ddc.storage.paths import ibf_subdir, path_info_from_cdb, DataBunch


__all__ = [
    'batch_with_pic_forms',
    'fake_tiff_handler',
    'ibf_mock',
    'set_durus_loglevel',
    'silence_durus_logging'
]

def ibf_mock(pics):
    def _create_entry(pic):
        if not isinstance(pic, str):
            pic = pic[0]
        return AttrDict(rec=AttrDict(codnr=pic))
    return AttrDict(
        image_entries=[_create_entry(pic) for pic in pics]
    )

def fake_tiff_handler(pic):
    if not isinstance(pic, str):
        pic = pic[1]
    return AttrDict(
        long_data2=AttrDict(
            rec=AttrDict(page_name=pic)
        )
    )

def batch_with_pic_forms(pics):
    def _form(pic):
        fields = [
            {'name': 'AUSSTELLUNGSDATUM', 'corrected_result': '01.01.2016'}
        ]
        if not isinstance(pic, str):
            pic = pic[0]
        cdb_form = CDBForm(fields, imprint_line_short=pic)
        return cdb_form

    forms = [_form(pic) for pic in pics]
    cdb_fp = BytesIO(CDBFile(forms).as_bytes())
    databunch = DataBunch(
        cdb=cdb_fp,
        ibf=create_ibf(nr_images=len(pics)),
        durus=create_durus_fixture(),
        ask=None,
    )
    batch = Batch.init_from_bunch(databunch, create_new_durus=False, access='read')
    batch.ibf = ibf_mock(pics)
    batch._tiff_handler = [fake_tiff_handler(pic) for pic in pics]
    return batch


def set_durus_loglevel(new_level):
    # Durus automatically logs some transaction info to stderr which is
    # annoying in the tests.
    # This helper method can be used to configure durus' logger with just one
    # line of code.
    logger = logging.getLogger('durus')
    previous_log_level = logger.level
    logger.setLevel(new_level)
    return previous_log_level

def silence_durus_logging():
    return set_durus_loglevel(new_level=logging.ERROR)

