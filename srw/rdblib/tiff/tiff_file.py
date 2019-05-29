
from collections import OrderedDict

from .tags import TiffTag, TAG_SIZE
from ..binary_format import BinaryFormat


class TiffFile:
    def __init__(self, byte_order=b'II', version=b'42', first_ifd=8):
        self.byte_order = byte_order
        self.version = version
        self.first_ifd = first_ifd
        self.tiff_images = []



class TiffImage:
    def __init__(self, tags=None, img_data=None):
        self.tags = OrderedDict(tags or {})
        self.img_data = img_data

    def write_bytes(self, fp):
        nr_tags = len(self.tags)
        ifd_spec = (
            ('nr_tags',           'H'),
            ('tag_data',          '%ds' % (nr_tags * TAG_SIZE)),
            ('next_ifd',          'i'),
        )
        ifd_writer = BinaryFormat(ifd_spec)
        ifd_size = ifd_writer.size

        tag_data_bytes = b''
        long_data = b''
        long_offset = ifd_size
        for tag_id, tag_value in sorted(self.tags.items()):
            tag_bytes, tag_long_data = TiffTag(tag_id, tag_value).to_bytes(long_offset=long_offset)
            tag_data_bytes += tag_bytes
            long_data += tag_long_data
            long_offset += len(tag_long_data)
        assert len(tag_data_bytes) == (nr_tags * TAG_SIZE)

        ifd_values = {
            'nr_tags': nr_tags,
            'tag_data': tag_data_bytes,
            'next_ifd': 0,
        }
        ifd_bytes = ifd_writer.to_bytes(ifd_values)
        fp.write(ifd_bytes)
        if long_data:
            fp.write(long_data)
        fp.write(self.img_data)

