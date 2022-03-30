# -*- coding: utf-8 -*-
"""srw-delete-image

Usage:
    srw-delete-image [--undelete] <IBF> <IMG>
"""

from pathlib import Path
import sys

from docopt import docopt

from ..ibf import ImageBatch, TiffHandler


__all__ = ['delete_image_main']

def delete_image_main(argv=sys.argv):
    arguments = docopt(__doc__, argv=argv[1:])
    img = int(arguments['<IMG>'])
    ibf_fn = arguments['<IBF>']
    undelete = arguments['--undelete']

    ibf_path = Path(ibf_fn)
    if not ibf_path.exists():
        sys.stderr.write(f'IBF-Datei "{ibf_fn}" existiert nicht.\n')
        sys.exit(2)

    ibf = ImageBatch(ibf_path, access='write')
    if ibf.image_count() < img:
        sys.stderr.write(f'IBF-Datei "{ibf_fn}" enthält nur {ibf.image_count()} Images.\n')
        sys.exit(3)

    img_idx = img - 1
    th = TiffHandler(ibf, index=img_idx)
    current_pic = th.long_data.rec.page_name
    actual_pic = th.long_data2.rec.page_name
    if undelete:
        if current_pic != 'DELETED':
            sys.stderr.write(f'Image "{img}" ist nicht als gelöscht markiert (PIC {current_pic}).\n')
            sys.exit(11)
        th.long_data.update_rec(page_name=actual_pic)
        print(f'Image #{img} wiederhergestellt (PIC {actual_pic})')
    else:
        if current_pic == 'DELETED':
            sys.stderr.write(f'Image "{img}" ist bereits gelöscht (PIC {actual_pic}).\n')
            sys.exit(10)
        print(f'loesche Image #{img} (PIC {current_pic})')
        th.long_data.update_rec(page_name='DELETED')
    th.update()
    ibf.close()

