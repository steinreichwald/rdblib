# encoding: utf-8
# This file was a part of MediaDrop (http://www.mediadrop.net),
# Copyright 2009-2014 MediaDrop contributors
# For the exact contribution history, see the git revision log.
# The source code in this file is is dual licensed under the MIT license or
# the GPLv3 or (at your option) any later version.

from __future__ import division

from decimal import Decimal

from babel import Locale
from babel.numbers import format_decimal
try:
    import bitmath
    has_bitmath = True
except ImportError:
    has_bitmath = False


__all__ = ['format_filesize', 'human_readable_size']

# -----------------------------------------------------------------------------
# Code initially from StackOverflow but modified by Felix Schwarz so the
# formatting aspect is separated from finding the right unit. Also it uses
# Python's Decimal instead of floats
# http://stackoverflow.com/a/1094933/138526
def human_readable_size(value):
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    for unit in ('B','KB','MB','GB'):
        if value < 1024 and value > -1024:
            return (value, unit)
        value = value / 1024
    return (value, 'TB')
# -----------------------------------------------------------------------------

def format_filesize(size, locale='en'):
    if has_bitmath and isinstance(size, bitmath.Bitmath):
        size = int(size.to_Byte())
    value, unit = human_readable_size(size)
    locale = Locale.parse(locale)
    return format_decimal(value, format=u'#,##0.#', locale=locale) + u'\xa0' + unit

