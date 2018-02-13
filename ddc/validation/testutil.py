# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from collections import OrderedDict


__all__ = ['valid_prescription_values']

def valid_prescription_values(*, with_pic=False, **values):
    # The idea is to return prescription values which should be considered as
    # "valid" in the test setup (as the field configuration is semi-hardcoded
    # at the moment we need to use the actual field names).
    from ddc.client.config import ALL_FIELD_NAMES
    valid_values = OrderedDict()
    for field_name in ALL_FIELD_NAMES:
        valid_values[field_name] = ''
    valid_values.update(values)
    if with_pic:
        pic_str = '10501200042024' if (with_pic == True) else with_pic
        valid_values['pic'] = pic_str
    return valid_values

