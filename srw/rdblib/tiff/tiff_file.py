
from collections import OrderedDict
import struct

from .tags import TiffTag, TAG_SIZE
from ..binary_format import BinaryFormat


__all__ = ['TiffImage', 'TiffFile']

class TiffFile:
    """Convenience class which wraps a simple TIFF parser/writer which can
    read/write Tiff metadata (aka tags/"IFD") exactly in the structure required
    by the old Walther software.
    This is not a full featured TIFF reader (not even baseline).
    """
    def __init__(self, byte_order=b'II', version=42, first_ifd=None, tiff_images=None):
        self.byte_order = byte_order
        self.version = version
        self.first_ifd = first_ifd
        self.tiff_images = list(tiff_images) if tiff_images else []
        self._header_writer = BinaryFormat(self.header)
        assert self.byte_order == b'II', 'only little ending encoding supported'
        assert self.version == 42
        if first_ifd is not None:
            assert self.first_ifd >= self.size

    header = (
        ('byte_order',        'H'),    # in IBF always 'II' = little endian
        ('version',           'H'),    # always 42 (0x2A 0x00) for TIFF
        ('first_ifd',         'i'),    # in IBF always 8
    )

    @property
    def size(self):
        return self._header_writer.size

    def write_bytes(self, fp):
        img_offset = self.first_ifd or self.size
        header_values = {
            'byte_order': _to_int(self.byte_order, 'H'),
            'version': _to_int(self.version, 'H'),
            'first_ifd': img_offset,
        }
        header_bytes = self._header_writer.to_bytes(header_values)
        fp.write(header_bytes)

        for tiff_img in self.tiff_images:
            tiff_img.write_bytes(fp, offset=img_offset)
            img_offset = fp.tell()

def _to_int(value, format_str):
    if isinstance(value, (int, )):
        return value
    return struct.unpack('<'+format_str, value)



class TiffImage:
    def __init__(self, tags=None, img_data=None):
        self.tags = OrderedDict(tags or {})
        self.img_data = img_data

    def write_bytes(self, fp, offset=0):
        tags = self.tags.copy()
        if (not tags.get(279)) and self.img_data:
            # StripByteCounts (= length of image for our limited case)
            tags[279] = len(self.img_data)
        nr_tags = len(tags)
        ifd_spec = (
            ('nr_tags',           'H'),
            ('tag_data',          '%ds' % (nr_tags * TAG_SIZE)),
            ('next_ifd',          'i'),
        )
        ifd_writer = BinaryFormat(ifd_spec)
        ifd_size = ifd_writer.size

        tag_data_bytes = b''
        long_data = b''
        long_offset = offset + ifd_size
        # The TIFF specification mandates that the entries in the IFD sorted in
        # ascending order (TIFF 6.0 specification, page 15). However the legacy
        # Walther software violates that rule and uses a "custom" ordering
        # (mostly ascending but some tags are out-of-place).
        # Therefore the caller must be able to specify the tag order explicitely.
        for tag_id, tag_value in tags.items():
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

