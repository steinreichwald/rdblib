# -*- coding: utf-8 -*-

from ..meta import WithBinaryMeta
from .ibf_format import Tiff


# rudimentary Tiff support
class TiffHandler(object):

    class Header(WithBinaryMeta):
        _struc = Tiff.header

    class IfdStruc(WithBinaryMeta):
        _struc = Tiff.ifd

    class TagStruc(WithBinaryMeta):
        _struc = Tiff.tag

    class LongData(WithBinaryMeta):
        _struc = Tiff.long_data


    def __init__(self, image_batch, index):
        self.filecontent = image_batch.filecontent
        entry = image_batch.image_entries[index]
        self.offset = entry.rec.image_offset
        self.image_size = entry.rec.image_size
        header = self.__class__.Header(self.filecontent, self.offset)
        assert header.rec.byte_order == 0x4949 # 'II'
        #
        # Note:
        # This special version of a tiff structure always has two almost identical
        # versions of the tiff header.
        # We use the fact that the old software only examines the first header.
        # We never write the second header, but use it to restore a deleted tiff record.

        # The first tiff header:
        ifd_ofs = self.offset + header.rec.first_ifd
        self.ifd = self.__class__.IfdStruc(self.filecontent, ifd_ofs)
        # tags ignored for now, just asssuming a fixed offset
        ext_ofs = ifd_ofs + self.ifd.record_size
        self.long_data = self.__class__.LongData(self.filecontent, ext_ofs)

        # The second tiff header:
        ifd2_ofs = self.offset + self.ifd.rec.next_ifd
        self.ifd2 = self.__class__.IfdStruc(self.filecontent, ifd2_ofs)
        ext_ofs2 = ifd2_ofs + self.ifd2.record_size
        self.long_data2 = self.__class__.LongData(self.filecontent, ext_ofs2)

    def update(self):
        ''' write changed tiff data '''
        #
        # Note:
        # The relevant classes in this container class derive from
        # "WithBinaryMeta".
        # Those classes are aware of attribute updates.
        # Whenever a field of X is changed, the field's name is inserted into
        # X.edited_fields.  Therefore, update() just examines that set to decide
        # if it needs to write data.
        #
        # This is a bit like ZODB/Durus handle changes to persistent data,
        # but in a very explicit way.

        buffer = self.filecontent
        long_data = self.long_data
        if long_data.edited_fields:
            data = long_data._get_binary()
            offset = long_data.offset
            buffer[offset:offset + len(data)] = data
            long_data.edited_fields.clear()
            self.filecontent.flush()
