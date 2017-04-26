# -*- coding: utf-8 -*-

import enum

from .ibf import TiffHandler


__all__ = []

@enum.unique
class Source(enum.Enum):
    CDB = 2
    IBF = 5

    AND = True
    OR  = False


class BatchForm(object):
    """
    BatchForm presents a unified interface for all form-related information and
    actions. It can access data from RDB, IBF and sqlite.
    Even though all information is (aka "should be") accessible via this class
    we still need something like a CDBForm, IBFImage, DBForm so data is also
    accessible even if we do not have all components at hand (e.g. IBF is
    missing).

    Please note that this is kind of "work in progress": I needed something
    like this for the ".is_deleted()" query so I decided to start building this
    class but it is by no means complete. Still I hope having this class helps
    building a more complete solution over time.
    """
    def __init__(self, batch, form_index):
        self.batch = batch
        self.form_index = form_index

    @property
    def ibf(self):
        return self.batch.ibf


    def pic(self):
        image_data = self.ibf.image_entries[self.form_index]
        ibf_rec_pic = image_data.rec.codnr
        if ibf_rec_pic != 'DELETED':
            return ibf_rec_pic

        if (self.batch._tiff_handlers is None):
            self.batch._tiff_handlers = [None] * self.ibf.image_count()
        th = self.batch._tiff_handlers[self.form_index]
        if th is None:
            th = TiffHandler(self.ibf, self.form_index)
            self.batch._tiff_handlers[self.form_index] = th
        ibf_long_pic = th.long_data2.rec.page_name
        return ibf_long_pic
