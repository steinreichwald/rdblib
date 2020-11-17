
from collections import OrderedDict
from datetime import datetime as DateTime

from .tag_specification import TIFF_TAG as TT
from .tiff_file import TiffImage
from .tiff_util import pad_tiff_bytes


__all__ = [
    'create_legacy_walther_image',
    'WaltherTiff'
]

# Legacy software stores some tag data before other "long data" (which is
# TIFF-compliant as the spec does not mandate any ordering). We want to produce
# exactly the same TIFF files so we need to replicate this ordering here.
tiff_long_order = (
    TT.XResolution,
    TT.YResolution,
    # other long data will be written afterwards, no need to specify all tag ids
)

class WaltherTiff(TiffImage):
    @classmethod
    def create(cls, *, width, height, pic, img_data, dpi=200):
        tags = walther_tags(
            width=width,
            height=height,
            dpi=dpi,
            page_name=pic,
            dt=DateTime.now()
        )
        return WaltherTiff(tags, img_data=img_data, long_order=tiff_long_order)


def create_legacy_walther_image(*, width, height, pic, img_data, img_description, dt=None):
    legacy_tags = walther_tags(
        width=width,
        height=height,
        page_name=pic,
        dpi=200,
        dt=dt,
        extra_tags={
            TT.ImageDescription: img_description,
            TT.ScannerManufacturer: 'WALTHER DATA GmbH Scan-Solutions',
            TT.ScannerModell: 'WALTHER MDT100/SM100U Image-System',
            TT.Software: 'WALTHER MDT100/SM100U Windows-Library',
            TT.Artist: 'D. Wünsch Scanprogramm'.encode('latin1'),
            TT.HostComputer: 'ARZ Wünsch GmbH'.encode('latin1'),
        }
    )
    return WaltherTiff(legacy_tags, img_data=img_data, long_order=tiff_long_order)


def walther_tags(*, width, height, page_name, dpi=200, dt=None, extra_tags=None):
    if dt is None:
        dt = DateTime.now()
    tags = OrderedDict([
        (254,               0),
        (TT.ImageWidth,     width),
        (TT.ImageLength,    height),
        (TT.BitsPerSample,  1),
        (TT.Compression,    4),
        (262,               0),
        (266,               1),
        (TT.DocumentName,           'REZEPT'),
        (TT.ImageDescription,       'DPI%03d_B/W' % dpi),
        (TT.ScannerManufacturer,    'Mcon Global - Michael Zeller'),
        (TT.ScannerModell,          'WALTHER HLS4'),
        (TT.StripOffsets,           TT.AUTO),
        (274,               1),
        (280,               0),
        (281,               1),
        (277,               1),
        (TT.RowsPerStrip,           height),
        (TT.StripByteCounts,        TT.AUTO),
        (TT.XResolution,    dpi),
        (TT.YResolution,    dpi),
        (TT.PageName,       page_name),
        (293,               0),
        (296,               2),
        (TT.Software,       'rdblib'),
        (TT.DateTime,       dt_to_string(dt)),
        (TT.Artist,         'Rechenzentrum fuer Berliner Apotheken Stein & Reichwald GmbH'),
        (TT.HostComputer,   'SRW'),
    ])
    if extra_tags:
        tags.update(extra_tags)

    for tag_id, tag_length in TAG_LENGTH.items():
        tags[tag_id] = pad_tiff_bytes(tags[tag_id], tag_length)
    return tags


TAG_LENGTH = {
    TT.DocumentName:        80,
    TT.ImageDescription:    20,
    TT.ScannerManufacturer: 40,
    TT.ScannerModell:       40,
    TT.PageName:            80,
    TT.Software:            40,
    TT.DateTime:            20,
    TT.Artist:              80,
    TT.HostComputer:        80,
}

def date_to_string(date):
    date_str = '%02d.%02d.%d' % (date.day, date.month, date.year)
    return date_str

def dt_to_string(dt):
    date_str = date_to_string(dt)
    time_str = '%02d:%02d:%02d' % (dt.hour, dt.minute, dt.second)
    return date_str + ' ' + time_str
