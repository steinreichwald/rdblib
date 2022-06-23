
from io import BytesIO

from srw.rdblib.tiff import create_walther_image_generated_by_srw, TIFF_TAG

from ._tiff_save import _save as tiff_save
from ..tiff_util import get_tiff_img_data


__all__ = ['as_bw_image', 'pil_image_as_walther_tiff']

def pil_image_as_walther_tiff(img, pic):
    bw_img = as_bw_image(img)
    tiff_fp = _serialize_as_tiff_image(bw_img)
    tiff_data = get_tiff_img_data(tiff_fp)
    walther_tiff = create_walther_image_generated_by_srw(
        tiff_data       = tiff_data,
        pic             = pic,
        img_description = 'REZEPT',
    )
    return walther_tiff

def as_bw_image(img):
    if img.mode == '1':
        # already black/white image
        return img
    img_q = img.quantize(colors=10)
    bw_img = img_q.convert('1')
    return bw_img

def _serialize_as_tiff_image(img):
    w_h = img.size
    height = w_h[1]
    img.encoderinfo = {
        'compression': 'group4',
        'tiffinfo': {
            TIFF_TAG.PhotometricInterpretation: 0,
            TIFF_TAG.RowsPerStrip: height,
        },
    }
    img.encoderconfig = ()
    tiff_fp = BytesIO()
    #_tiff_save._save(img, tiff_fp, 'dummy.tiff', encoderinfo=encoderinfo, encoderconfig=())
    tiff_save(img, tiff_fp, 'dummy.tiff')
    tiff_fp.seek(0)
    return tiff_fp
