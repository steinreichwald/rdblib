# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from collections import OrderedDict
from datetime import date as Date
from io import BytesIO
import os

from ..batch import Batch
from ..cdb import create_cdb_with_form_values, CDBFile, CDBForm
from ..ibf.testutil import create_ibf
from ..lib import AttrDict
from ..paths import assemble_new_path, guess_path, DataBunch
from ..sqlite import create_sqlite_db
from .bindiff import colorized_diff


__all__ = [
    'add_pic',
    'batch_with_pic_forms',
    'colorized_diff',
    'create_cdb_and_ibf_file',
    'generate_pic',
    'valid_prescription_values',
]

VALIDATED_FIELDS = (
    'ABGABEDATUM',
    'AUSSTELLUNGSDATUM',
    'BSNR',
    'GEBURTSDATUM',
    'LANR',
)

def add_pic(form_values, pic_str):
    if not pic_str:
        return
    # pic_str=True means fixed ("random") PIC, otherwise use the provided PIC str
    pic_str = '10501200042024' if (pic_str == True) else pic_str
    form_values['pic'] = pic_str

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
    add_pic(valid_values, pic_str=with_pic)
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
    batch = Batch.init_from_bunch(databunch, create_persistent_db=False, access='read')
    batch.ibf = ibf_mock(pics)
    batch._tiff_handlers = [fake_tiff_handler(pic) for pic in pics]
    return batch


def generate_pic(scan_nr=1):
    today = Date.today()
    year_digit_str = str(today.year)[-1]
    month_str = '%02d' % today.month
    date_prefix = year_digit_str + month_str
    customer_str = '123'
    nr_str = '%05d' % scan_nr
    return date_prefix + customer_str + nr_str + '024'


def create_cdb_and_ibf_file(cdb_path, form_data=None, *, ibf_dir=None, pic_nrs=None, valid_values_generator=None):
    """Create a xDB file and a corresponding IBF."""
    if form_data is None:
        form_data = pic_nrs
    if valid_values_generator is None:
        valid_values_generator = valid_prescription_values
    _form_data = []
    for i, data in enumerate(form_data):
        is_pic = isinstance(data, str)
        if is_pic:
            pic_nr = data
            extra_fields = {}
        elif (pic_nrs is not None) and (i < len(pic_nrs)):
            pic_nr = pic_nrs[i]
            extra_fields = data
        else:
            pic_nr = generate_pic(scan_nr=i+1)
            extra_fields = data
        form_values = valid_values_generator(with_pic=pic_nr, **extra_fields)
        _form_data.append(form_values)
    pic_nrs = [form_values['pic'] for form_values in _form_data]

    cdb_fp = create_cdb_with_form_values(_form_data, filename=cdb_path)
    cdb_fp.close()

    if ibf_dir is None:
        ibf_path = guess_path(cdb_path, 'IBF')
        ibf_dir = os.path.dirname(ibf_path)
    else:
        ibf_path = assemble_new_path(cdb_path, new_dir=ibf_dir, new_extension='IBF')
    os.makedirs(ibf_dir, exist_ok=True)
    ibf_fp = create_ibf(
        nr_images=len(pic_nrs),
        pic_nrs=pic_nrs,
        fake_tiffs=False,
        filename=ibf_path
    )
    ibf_fp.close()
    return (cdb_path, ibf_path)

