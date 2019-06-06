# -*- coding: utf-8 -*-

from collections import namedtuple

from smart_constants import attrs, BaseConstantsClass


__all__ = ['FieldType', 'TiffTags']

#  copy of smart_constants.attrs so we can have "**data" instead of "data"
class _attrs(object):
    counter = 0

    def __init__(self, label=None, visible=True, value=None, **data):
        self.label = label
        self.visible = visible
        self.value = value
        self.data = data
        # declaration of attributes should affect ordering of items later on
        # (e.g. in a select widget). In Python 2 we have to use some workarounds
        # to make that happen.
        # http://stackoverflow.com/questions/4459531/how-to-read-class-attributes-in-the-same-order-as-declared
        self._order = attrs.counter
        self.__class__.counter += 1

    def __repr__(self):
        classname = self.__class__.__name__
        parameters = (classname, self.label, self.visible, self.value, self.data, self._order)
        return '%s(label=%r, visible=%r, value=%r, data=%r, _order=%r)' % parameters


class FieldType(BaseConstantsClass):
    BYTE        = 1, _attrs(bytes=1)     # 8-bit unsigned integer
    ASCII       = 2, _attrs(bytes=len)   # n × 8-bit byte that contains a 7-bit ASCII code; the last byte must be NUL (binary zero)
    SHORT       = 3, _attrs(bytes=2)     # 16-bit unsigned integer
    LONG        = 4, _attrs(bytes=4)     # 32-bit unsigned integer
    RATIONAL    = 5, _attrs(bytes=2*4)   # two LONGs: the first represents the numerator of afraction; the second, the denominator

# TIFF specification allows SHORT or LONG but our legacy software always uses
# SHORT here
FieldType._SHORT_OR_LONG = FieldType.SHORT



TiffTagSpecification = namedtuple('TiffTagSpecification', ('name', 'type'))

FT = FieldType
TTSpec = TiffTagSpecification

TiffTags = {
    256: TTSpec('ImageWidth', FT._SHORT_OR_LONG),
    257: TTSpec('ImageLength', FT._SHORT_OR_LONG),
    258: TTSpec('BitsPerSample', FT.SHORT),
    259: TTSpec('Compression', FT.SHORT),

    269: TTSpec('DocumentName', FT.ASCII),
    270: TTSpec('ImageDescription', FT.ASCII),
}

