# -*- coding: utf-8 -*-

from collections import namedtuple

from smart_constants import attrs, BaseConstantsClass


__all__ = ['FieldType', 'TiffTags', 'TIFF_TAG']

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
# same as above but legacy software uses LONG
FieldType._LONG_OR_SHORT = FieldType.LONG


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
    273: TTSpec('StripOffsets', FT._LONG_OR_SHORT),
    274: TTSpec('Orientation', FT.SHORT),       # 1-8
    277: TTSpec('SamplesPerPixel', FT.SHORT),   # 1-8
    278: TTSpec('RowsPerStrip', FT._LONG_OR_SHORT),
    279: TTSpec('StripByteCounts', FT._LONG_OR_SHORT),   # aka "image data bytes" for us
    280: TTSpec('MinSampleValue', FT.SHORT),
    281: TTSpec('MaxSampleValue', FT.SHORT),
    282: TTSpec('XResolution', FT.RATIONAL),
    283: TTSpec('YResolution', FT.RATIONAL),
    285: TTSpec('PageName', FT.ASCII),          # "name of the page from which this image was scanned"
    293: TTSpec('T6Options', FT.LONG),
    # 296: TIFF specification says SHORT but the legacy software uses LONG
    296: TTSpec('ResolutionUnit', FT.LONG),     # 2 = "inch"
    305: TTSpec('Software', FT.ASCII),          # "Name and version number of the software package(s) used to create the image."
    306: TTSpec('DateTime', FT.ASCII),          # "Date and time of image creation" (format "YYYY:MM:DD HH:MM:SS")
    315: TTSpec('Artist', FT.ASCII),            # "Person who created the image"
    316: TTSpec('HostComputer', FT.ASCII),      # "The computer and/or operating system in use at the time of image creation."
}


class TIFF_TAG:
    NewSubfileType      = 254
    ImageWidth          = 256
    ImageLength         = 257
    BitsPerSample       = 258
    Compression         = 259
    PhotometricInterpretation = 262
    FillOrder           = 266

    DocumentName        = 269
    ImageDescription    = 270
    ScannerManufacturer = 271
    ScannerModell       = 272
    StripOffsets        = 273
    Orientation         = 274

    SamplesPerPixel     = 277
    RowsPerStrip        = 278
    StripByteCounts     = 279
    MinSampleValue      = 280
    MaxSampleValue      = 281
    XResolution         = 282
    YResolution         = 283
    PageName            = 285
    T6Options           = 293
    ResolutionUnit      = 296
    Software            = 305
    DateTime            = 306
    Artist              = 315
    HostComputer        = 316

    AUTO                = None

