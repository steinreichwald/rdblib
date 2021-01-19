# -*- coding: utf-8 -*-

from timeit import default_timer as timer

from ..lib import l_
from ..meta import WithBinaryMeta
from ..mmap_file import MMapFile
from ..utils import filecontent
from .ibf_format import IBFFormat


__all__ = ['ImageBatch']

class ImageBatchHeader(WithBinaryMeta):
    _struc = IBFFormat.batch_header


class Image(WithBinaryMeta):
    _struc = IBFFormat.index_entry


class ImageBatch(object):

    def __init__(self, image_job, delay_load=False, access='write', log=None):
        if hasattr(image_job, 'close'):
            self.mmap_file = image_job
        else:
            self.mmap_file = MMapFile(image_job, access=access, log=log)

        self.log = l_(log)
        self.header = None
        self.image_entries = None
        self._load_delayed = delay_load
        self.load_header()
        self.load_directories()

    def close(self):
        self.mmap_file.close()

    def load_header(self):
        start = timer()
        self.header = ImageBatchHeader(self.filecontent)
        duration = timer() - start
        self.log.debug('loading IBF header took %.5f seconds', duration)

    @property
    def filecontent(self):
        return filecontent(self.mmap_file)

    def load_directories(self):
        def _get_subindex(offset):
            entries = []
            image_count = -1
            while image_count != 0:
                entry = Image(self.filecontent, offset)
                entries.append(entry)
                if image_count == -1:
                    offset_next_index = entry.rec.offset_next_indexblock
                    image_count = entry.rec.images_in_indexblock
                image_count -= 1
                offset += len(entry)
            return entries, offset_next_index

        start = timer()
        offset = self.header.rec.offset_first_index
        self.image_entries = []
        while offset != 0:
            directory, offset = _get_subindex(offset)
            self.image_entries += directory
        duration = timer() - start
        self.log.debug('loading %d image entries from IBF took %.5f seconds', len(self.image_entries), duration)

    def get_tiff_image(self, index):
        entry = self.image_entries[index]
        return self.filecontent[entry.rec.image_offset:
                                entry.rec.image_offset + entry.rec.image_size]

    def image_count(self):
        return len(self.image_entries)

    # XXX this is right now a bit ugly, since we need to go though this structure
    # and not the image struc, directly. Will change...
    def update_entry(self, entry):
        ''' write a changed index entry '''
        assert isinstance(entry, Image)
        buffer = self.filecontent
        if entry.edited_fields:
            data = entry._get_binary()
            offset = entry.offset
            buffer[offset:offset + len(data)] = data
            entry.edited_fields.clear()
            self.mmap_file.flush()
