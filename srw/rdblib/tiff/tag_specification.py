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
    254: TTSpec('NewSubfileType', FT.LONG),     # 0-7 (bitmask)
    256: TTSpec('ImageWidth', FT._SHORT_OR_LONG),
    257: TTSpec('ImageLength', FT._SHORT_OR_LONG),
    258: TTSpec('BitsPerSample', FT.SHORT),
    259: TTSpec('Compression', FT.SHORT),       # 1-6 or 32773
    262: TTSpec('PhotometricInterpretation', FT.SHORT),
    266: TTSpec('FillOrder', FT.SHORT),         # 1 or 2
    269: TTSpec('DocumentName', FT.ASCII),
    270: TTSpec('ImageDescription', FT.ASCII),
    271: TTSpec('Make', FT.ASCII),              # "scanner manufacturer"
    272: TTSpec('Model', FT.ASCII),             # "scanner model name or number"
    273: TTSpec('StripOffsets', FT._SHORT_OR_LONG),
    274: TTSpec('Orientation', FT.SHORT),       # 1-8
    277: TTSpec('SamplesPerPixel', FT.SHORT),   # 1-8
    278: TTSpec('RowsPerStrip', FT._SHORT_OR_LONG),
    279: TTSpec('StripByteCounts', FT._SHORT_OR_LONG),   # aka "image data bytes" for us
    280: TTSpec('MinSampleValue', FT.SHORT),
    281: TTSpec('MaxSampleValue', FT.SHORT),
    282: TTSpec('XResolution', FT.RATIONAL),
    283: TTSpec('YResolution', FT.RATIONAL),
    285: TTSpec('PageName', FT.ASCII),          # "name of the page from which this image was scanned"
    293: TTSpec('T6Options', FT.LONG),
    296: TTSpec('ResolutionUnit', FT.SHORT),    # 2 = "inch"
    305: TTSpec('Software', FT.ASCII),          # "Name and version number of the software package(s) used to create the image."
    306: TTSpec('DateTime', FT.ASCII),          # "Date and time of image creation" (format "YYYY:MM:DD HH:MM:SS")
    315: TTSpec('Artist', FT.ASCII),            # "Person who created the image"
    316: TTSpec('HostComputer', FT.ASCII),      # "The computer and/or operating system in use at the time of image creation."
}

