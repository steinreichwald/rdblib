
from ._testutil import load_tiff_dummy_img
from ..tiff_file import TiffFile
from ..walther_tiff import WaltherTiff


__all__ = ['create_dual_page_tiff_file']

def create_dual_page_tiff_file(pic_str):
    img1 = load_tiff_dummy_img()
    width, height = img1.size
    tiff_img1 = WaltherTiff.create(width=width, height=height, img_data=img1.data, pic=pic_str)

    img2 = load_tiff_dummy_img()
    tiff_img2 = WaltherTiff.create(width=width, height=height, img_data=img2.data, pic=pic_str)
    tiff_file = TiffFile(tiff_images=[tiff_img1, tiff_img2])
    return tiff_file

