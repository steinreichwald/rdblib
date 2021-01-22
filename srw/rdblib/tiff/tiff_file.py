
from collections import OrderedDict
from io import BytesIO
import math
import struct

from .tags import TiffTag, TAG_SIZE
from .tag_specification import TIFF_TAG as TT
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

        for img_idx, tiff_img in enumerate(self.tiff_images):
            is_last_image = (img_idx + 1 == len(self.tiff_images))
            tiff_img.write_bytes(fp, is_last_image=is_last_image, offset=img_offset)
            img_offset = fp.tell()

    def to_bytes(self):
        buffer = BytesIO()
        self.write_bytes(buffer)
        buffer.seek(0)
        return buffer.read()


def _to_int(value, format_str):
    if isinstance(value, (int, )):
        return value
    return struct.unpack('<'+format_str, value)



class TiffImage:
    def __init__(self, tags=None, img_data=None, long_order=None):
        self.tags = OrderedDict(tags or {})
        self.img_data = img_data
        self.long_order = long_order

    def write_bytes(self, fp, is_last_image=True, offset=0):
        tags = self.tags.copy()
        # add tags so "nr_tags" is correct
        value_strip_offsets = tags.setdefault(TT.StripOffsets, TT.AUTO)
        if (not tags.get(TT.StripByteCounts)) and self.img_data:
            # StripByteCounts (= length of image for our limited case)
            tags[TT.StripByteCounts] = len(self.img_data)
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

        tag_id_bytes = {}
        # The TIFF specification mandates that the entries in the IFD sorted in
        # ascending order (TIFF 6.0 specification, page 15). However the legacy
        # Walther software violates that rule and uses a "custom" ordering
        # (mostly ascending order but some tags are out-of-place).
        # Therefore the caller must be able to specify the tag order explicitely.
        # The "long" values (> 4 bytes) are placed in yet another order (though
        # that is explicitely allowed by the spec at least).
        long_order = self.long_order or tuple(tags.keys())
        for tag_id in sort_by_list(tags, ordering=long_order, default=9999):
            if (tag_id == TT.StripOffsets) and (value_strip_offsets is TT.AUTO):
                continue
            tag_value = tags[tag_id]
            tag_bytes, tag_long_data = TiffTag(tag_id, tag_value).to_bytes(long_offset=long_offset)
            tag_id_bytes[tag_id] = tag_bytes
            long_data += tag_long_data
            long_offset += len(tag_long_data)

        img_pre_padding = b''
        if value_strip_offsets is None:
            strip_offset = align_to_8(long_offset)
            nr_pad_bytes = strip_offset - long_offset
            img_pre_padding = nr_pad_bytes * b'\x00'
            tag_bytes, tag_long_data = TiffTag(273, strip_offset).to_bytes()
            assert (not tag_long_data)
            tag_id_bytes[TT.StripOffsets] = tag_bytes

        # the legacy software uses an arbitrary ordering of tags so we just
        # use the order as specified by the caller.
        for tag_id in tags:
            tag_bytes = tag_id_bytes[tag_id]
            tag_data_bytes += tag_bytes

        offset_next_ifd = 0
        if not is_last_image:
            # long_offset was incremented when tag values were serialized above
            offset_end_of_long_data = long_offset
            offset_next_ifd = offset_end_of_long_data + len(img_pre_padding + self.img_data)
        ifd_values = {
            'nr_tags': nr_tags,
            'tag_data': tag_data_bytes,
            'next_ifd': offset_next_ifd,
        }
        ifd_bytes = ifd_writer.to_bytes(ifd_values)
        fp.write(ifd_bytes + long_data + img_pre_padding + self.img_data)

    def to_bytes(self, **tiff_args):
        buffer = BytesIO()
        self.write_bytes(buffer, **tiff_args)
        buffer.seek(0)
        return buffer.read()


def align_to_8(value):
    return math.ceil(value / 8) * 8

def align_to_8_offset(value):
    return align_to_8(value) - value

def sort_by_list(values, ordering, default=-1):
    index_of = lambda v: ordering.index(v) if (v in ordering) else default
    sort_keys = [index_of(v) for v in values]
    return [v for (_, v) in sorted(zip(sort_keys, values))]

