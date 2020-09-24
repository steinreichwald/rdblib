# -*- coding: utf-8 -*-
"""srw-extract-image

Dieses Skript extrahiert das angebene Bild aus einer IBF-Datei
(bzw. alle Bilder, falls "--all" verwendet wurde).

Usage:
    srw-extract-image <IBF_PATH> <FORM_NR> <OUTPUT_PATH>
    srw-extract-image [options] <IBF_PATH> <OUTPUT_PATH>
    srw-extract-image -h

Options:
    --all           Extract all images
    --tiff          Store images as tiff (same as in IBF)
    -h, --help      Show this screen
"""

from io import BytesIO
import os
import sys

from docopt import docopt
from PIL import Image

from ..ibf import ImageBatch


__all__ = ['extract_image_main']

def _store_image(ibf, form_idx, target_path, use_tiff=False):
    tiff_data = ibf.get_tiff_image(form_idx)
    if use_tiff:
        with open(target_path, 'wb') as img_fp:
            img_fp.write(tiff_data)
    else:
        img = Image.open(BytesIO(tiff_data))
        img.seek(1)
        img.save(target_path, quality=90)
        img.close()


def extract_image_main():
    arguments = docopt(__doc__)
    extract_all_images = arguments['--all']
    use_tiff = arguments['--tiff']
    ibf_arg = arguments['<IBF_PATH>']
    form_nr = int(arguments['<FORM_NR>']) if not extract_all_images else None
    output_arg = arguments['<OUTPUT_PATH>']

    ibf_path = os.path.abspath(ibf_arg)
    if not os.path.exists(ibf_path):
        sys.stderr.write('IBF-Datei "%s" existiert nicht.\n' % ibf_arg)
        sys.exit(20)

    if (form_nr is not None) and (form_nr < 1):
        sys.stderr.write('FORM_NR muss größer/gleich "1" sein ("%s").\n' % arguments['<FORM_NR>'])
        sys.exit(20)

    img_extension = 'tiff' if use_tiff else 'jpg'
    output_path = os.path.abspath(output_arg)
    if extract_all_images:
        output_dir = output_path
        output_filename = None
    elif os.path.isfile(output_path) or output_path.lower().endswith('.'+img_extension):
        output_dir = os.path.dirname(output_path)
        output_filename = os.path.basename(output_path)
    else:
        output_dir = output_path
        output_filename = None
    if not os.path.exists(output_dir):
        sys.stderr.write('Zielverzeichnis "%s" existiert nicht.\n' % os.path.basename(output_arg))
        sys.exit(20)

    get_target_path = lambda form_nr: os.path.join(output_dir, output_filename or 'form-%03d.%s' % (form_nr, img_extension))

    ibf = ImageBatch(ibf_path, delay_load=False, access='read')
    nr_forms = ibf.image_count()
    if not extract_all_images:
        if nr_forms < form_nr:
            sys.stderr.write('Kein Formular mit Nr. %s, IBF enthält nur %d Belege.\n' % (arguments['<FORM_NR>'], nr_forms))
            sys.exit(21)
        form_idx = form_nr - 1
        target_path = get_target_path(form_nr)
        _store_image(ibf, form_idx, target_path, use_tiff=use_tiff)
    else:
        for form_idx in range(nr_forms):
            form_nr = form_idx+1
            target_path = get_target_path(form_nr)
            _store_image(ibf, form_idx, target_path, use_tiff=use_tiff)
