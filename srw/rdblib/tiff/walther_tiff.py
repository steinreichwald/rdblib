
from collections import OrderedDict
from datetime import datetime as DateTime
import re

from PIL import Image

from .tag_specification import TIFF_TAG as TT
from .tiff_file import TiffFile, TiffImage
from .tiff_util import get_tiff_img_data, pad_tiff_bytes


__all__ = [
    'create_legacy_walther_image',
    'dt_from_string',
    'inject_pic_in_tiff',
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
    def create(cls, *, width, height, pic, img_data, dpi=200, dt=None):
        tags = walther_tags(
            width     = width,
            height    = height,
            dpi       = dpi,
            page_name = pic,
            dt        = dt,
        )
        return WaltherTiff(tags, img_data=img_data, long_order=tiff_long_order)


def create_legacy_walther_image(*, width, height, pic, img_data, img_description, dt=None):
    legacy_tags = walther_tags(
        width      = width,
        height     = height,
        page_name  = pic,
        dpi        = 200,
        dt         = dt,
        extra_tags = {
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
        (254,               0), # NewSubfileType ("general indication of the kind of data contained in this subfile"), default = 0
        (TT.ImageWidth,     width),
        (TT.ImageLength,    height),
        (TT.BitsPerSample,  1),
        (TT.Compression,    4),
        (262,               0), # Photometric Interpretation: 0 = "schwarz auf weiß"
        (266,               1), # Fill Order: 1 = "von oben links nach unten rechts"
        (TT.DocumentName,           'REZEPT'),
        (TT.ImageDescription,       'DPI%03d_B/W' % dpi),
        (TT.ScannerManufacturer,    'Mcon Global - Michael Zeller'),
        (TT.ScannerModell,          'WALTHER HLS4'),
        (TT.StripOffsets,           TT.AUTO),
        (274,               1), # Orientation
        (280,               0), # MinSampleValue ("minimum component value used"), TIFF default = 0
        (281,               1), # MaxSampleValue ("maximum component value used"), TIFF default = 2**(BitsPerSample) - 1
        (277,               1), # Samples Per Pixel (1 = Graustufen)
        (TT.RowsPerStrip,           height),
        (TT.StripByteCounts,        TT.AUTO),
        (TT.XResolution,    dpi),
        (TT.YResolution,    dpi),
        (TT.PageName,       page_name),
        (293,               0), # T6Options
        (296,               2), # Resolution Unit (2 = "Zoll")
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

def dt_from_string(date_str):
    match = re.search('^(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2}):(\d{2})$', date_str)
    day, month, year, hour, minute, second = map(int, match.groups())
    return DateTime(year, month, day, hour, minute, second)

def inject_pic_in_tiff(tiff_path, pic_str):
    pillow_img = Image.open(str(tiff_path))
    tiff_imgs = []
    for page_idx, tiff_info in enumerate(get_tiff_img_data(tiff_path)):
        pillow_img.seek(page_idx)

        tiff_tags = dict(pillow_img.tag_v2.items())
        dpi_x = tiff_tags[TT.XResolution]
        dpi_y = tiff_tags[TT.YResolution]
        assert (dpi_x == dpi_y)
        dt = dt_from_string(tiff_tags[TT.DateTime])

        tiff_img = WaltherTiff.create(
            width    = tiff_info.width,
            height   = tiff_info.height,
            # TT.XResolution from pillow returns a float, but we need int
            dpi      = int(dpi_x),
            img_data = tiff_info.img_data,
            pic      = pic_str,
            dt       = dt,
        )
        tiff_imgs.append(tiff_img)
    pillow_img.close()

    tf = TiffFile(tiff_images=tiff_imgs)
    tiff_bytes = tf.to_bytes()
    return tiff_bytes

