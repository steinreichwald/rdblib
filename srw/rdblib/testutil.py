# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from collections import OrderedDict
from contextlib import contextmanager
from datetime import date as Date
from io import BytesIO
import shutil
from tempfile import mkdtemp

from .batch import Batch
from .cdb import CDBFile, CDBForm
from .ibf import create_ibf
from .lib import AttrDict
from .paths import DataBunch
from .sqlite import create_sqlite_db


__all__ = [
    'batch_with_pic_forms',
    'valid_prescription_values',
    'use_tempdir',
]

VALIDATED_FIELDS = (
    'ABGABEDATUM',
    'AUSSTELLUNGSDATUM',
    'BSNR',
    'GEBURTSDATUM',
    'LANR',
)

def valid_prescription_values(*, with_pic=False, **values):
    # The idea is to return prescription values which should be considered as
    # "valid" in the test setup (as the field configuration is semi-hardcoded
    # at the moment we need to use the actual field names).
    valid_values = OrderedDict()
    for field_name in VALIDATED_FIELDS:
        valid_values[field_name] = ''
    today = Date.today()
    valid_values.update({
        'LANR': '240000601',
        'BSNR': '179999900',
        'GEBURTSDATUM': '30.08.1950',
        'AUSSTELLUNGSDATUM': '%02d.%02d.%02d' % (today.day, today.month, today.year),
        'ABGABEDATUM': '%02d%02d%02d' % (today.day, today.month, today.year),
    })
    valid_values.update(values)
    if with_pic:
        # with_pic='...' will ensure we use a specific PIC
        pic_str = '10501200042024' if (with_pic == True) else with_pic
        valid_values['pic'] = pic_str
    return valid_values


def _update_attr(container, **kwargs):
    for attr_name, value in kwargs.items():
        setattr(container, attr_name, value)

def ibf_mock(pics):
    def _create_entry(pic):
        if not isinstance(pic, str):
            pic = pic[0]

        data = AttrDict({
            'rec': AttrDict(codnr=pic),
        })
        data['update_rec'] = lambda codnr=None: _update_attr(data.rec, codnr=codnr)
        return data
    return AttrDict(
        image_entries=[_create_entry(pic) for pic in pics],
        update_entry = lambda x: None
    )

def fake_tiff_handler(pic):
    if not isinstance(pic, str):
        pic = pic[1]

    long_data = AttrDict({
        'rec': AttrDict(page_name=pic),
    })
    long_data['update_rec'] = lambda page_name=None: _update_attr(long_data.rec, page_name=page_name)
    return AttrDict(
        long_data=long_data,
        long_data2=AttrDict(
            rec=AttrDict(page_name=pic)
        ),
    )

def batch_with_pic_forms(pics, *, model=None):
    field_names = ('AUSSTELLUNGSDATUM',)
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
        db=create_sqlite_db(model=model),
        ask=None,
    )
    batch = Batch.init_from_bunch(databunch, create_persistent_db=False, access='read', field_names=field_names)
    batch.ibf = ibf_mock(pics)
    batch._tiff_handlers = [fake_tiff_handler(pic) for pic in pics]
    return batch


@contextmanager
def use_tempdir():
    tempdir_path = mkdtemp()
    yield tempdir_path
    shutil.rmtree(tempdir_path)

