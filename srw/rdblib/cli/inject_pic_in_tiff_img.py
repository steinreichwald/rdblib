# -*- coding: utf-8 -*-
"""srw-inject-pic-into-tiff

Usage:
    srw-inject-pic-into-tiff [--replace] <TIFF> <PIC> [<TARGET>]
"""

from pathlib import Path
import sys

from docopt import docopt
from PIL import Image

from ..tiff import dt_from_string, get_tiff_img_data, TiffFile, WaltherTiff, TIFF_TAG as TT


__all__ = ['inject_pic_in_tiff_img_main']

def inject_pic_in_tiff_img_main(argv=sys.argv):
    arguments = docopt(__doc__, argv=argv[1:])
    tiff_path = Path(arguments['<TIFF>'])
    pic_str = arguments['<PIC>']
    replace = arguments['--replace']
    target = arguments['<TARGET>']
    if replace and target:
        sys.stderr.write('"--replace" kann nicht mit <TARGET> zusammen verwendet werden.\n')
        sys.exit(1)
    elif (not replace) and (not target):
        sys.stderr.write('Bitte <TARGET> angeben oder "--replace" zum Überschreiben der Originaldateien verwenden.\n')
        sys.exit(1)

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
    if replace:
        output_path = tiff_path
        mode = 'wb'
    else:
        if target.lower().endswith('.tiff'):
            output_path = Path(target)
        else:
            output_path = Path(target) / tiff_path.name
        if output_path.exists():
            sys.stderr.write(f'Zieldatei {str(output_path)} existiert bereits\n')
            sys.exit(10)
        mode = 'xb'
    with output_path.open(mode) as output_fp:
        output_fp.write(tiff_bytes)

