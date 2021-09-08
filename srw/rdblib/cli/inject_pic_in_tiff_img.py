# -*- coding: utf-8 -*-
"""srw-inject-pic-into-tiff

Usage:
    srw-inject-pic-into-tiff [--replace] <TIFF> <PIC> [<TARGET>]
"""

from pathlib import Path
import sys

from docopt import docopt

from ..tiff import inject_pic_in_tiff


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

    tiff_bytes = inject_pic_in_tiff(tiff_path, pic_str)
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

