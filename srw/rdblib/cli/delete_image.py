# -*- coding: utf-8 -*-
"""srw-delete-image

Löscht ein oder mehrere Images aus einer IBF-Datei.

<IMG> ist dabei die Position des Images in der IBF-Datei.
Es können auch mehrere Images auf einmal angegeben werden (z.B. "5-7").

Usage:
    srw-delete-image [--undelete] <IBF> <IMG>
"""

from pathlib import Path
import re
import sys

from docopt import docopt

from ..ibf import ImageBatch, TiffHandler


__all__ = ['delete_image_main']

def delete_image_main(argv=sys.argv):
    arguments = docopt(__doc__, argv=argv[1:])
    img_str = arguments['<IMG>']
    m_range = re.search(r'^(\d+)\-(\d+)$', img_str)
    if m_range:
        img_start, img_end = map(int, m_range.groups())
    else:
        img_start = int(arguments['<IMG>'])
        img_end = img_start
    ibf_fn = arguments['<IBF>']
    undelete = arguments['--undelete']

    if img_start > img_end:
        sys.stderr.write(f'erste Image-Position (#{img_start}) muss kleiner sein als zweite Position (#{img_end}).\n')
        sys.exit(1)

    ibf_path = Path(ibf_fn)
    if not ibf_path.exists():
        sys.stderr.write(f'IBF-Datei "{ibf_fn}" existiert nicht.\n')
        sys.exit(2)

    ibf = ImageBatch(ibf_path, access='write')
    if ibf.image_count() < img_end:
        sys.stderr.write(f'IBF-Datei "{ibf_fn}" enthält nur {ibf.image_count()} Images.\n')
        sys.exit(3)

    for img in range(img_start, img_end+1):
        img_idx = img - 1
        th = TiffHandler(ibf, index=img_idx)
        current_pic = th.long_data.rec.page_name
        actual_pic = th.long_data2.rec.page_name
        if undelete:
            if current_pic != 'DELETED':
                sys.stderr.write(f'Image "{img}" ist nicht als gelöscht markiert (PIC {current_pic}).\n')
                continue
            th.long_data.update_rec(page_name=actual_pic)
            print(f'Image #{img} wiederhergestellt (PIC {actual_pic})')
        else:
            if current_pic == 'DELETED':
                sys.stderr.write(f'Image "{img}" ist bereits gelöscht (PIC {actual_pic}).\n')
                continue
            print(f'loesche Image #{img} (PIC {current_pic})')
            th.long_data.update_rec(page_name='DELETED')
        th.update()
    ibf.close()

