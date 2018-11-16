# -*- coding: utf-8 -*-
"""srw-extract-image

Dieses Skript extrahiert ein Bild aus einer IBF-Datei.

Usage:
    srw-extract-image [options] <IBF_PATH> <FORM_NR> <OUTPUT_PATH>

Options:
    -h, --help      Show this screen
"""

from io import BytesIO
import os
import sys

from docopt import docopt
from PIL import Image

from ..ibf import ImageBatch


__all__ = ['extract_image_main']

def _store_image(ibf, form_idx, target_path):
    tiff_data = ibf.get_tiff_image(form_idx)
    img = Image.open(BytesIO(tiff_data))
    img.seek(1)
    img.save(target_path, quality=90)
    img.close()


def extract_image_main():
    arguments = docopt(__doc__)
    ibf_arg = arguments['<IBF_PATH>']
    form_nr = int(arguments['<FORM_NR>'])
    output_arg = arguments['<OUTPUT_PATH>']

    ibf_path = os.path.abspath(ibf_arg)
    if not os.path.exists(ibf_path):
        sys.stderr.write('IBF-Datei "%s" existiert nicht.\n' % ibf_arg)
        sys.exit(20)
    output_path = os.path.abspath(output_arg)
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        sys.stderr.write('Zielverzeichnis "%s" existiert nicht.\n' % os.path.basename(output_arg))
        sys.exit(20)
    if form_nr < 1:
        sys.stderr.write('FORM_NR muss größer/gleich "1" sein ("%s").\n' % arguments['<FORM_NR>'])
        sys.exit(20)

    ibf = ImageBatch(ibf_path, delay_load=False, access='read')
    nr_forms = ibf.image_count()
    if nr_forms < form_nr:
        sys.stderr.write('Kein Formular mit Nr. %s, IBF enthält nur %d Belege.\n' % (arguments['<FORM_NR>'], nr_forms))
        sys.exit(21)

    _store_image(ibf, form_nr, target_path)
