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

    # LATER: Refactor arguments for is_deleted(...)
    # ideally the API should look like this:
    #    .is_deleted(Source.CDB)
    #    .is_deleted(Source.IBF)
    #    .is_deleted(Source.CDB | Source.IBF)
    #    .is_deleted(Source.CDB & Source.IBF)
    def is_deleted(self, *, cdb=True, ibf=True, operator=Source.OR):
        """Return True if the form has been deleted. Without parameters this
        is true if the form is marked as "DELETED" in the CDB or the IBF.

        This decision is surprisingly complicated because the legacy software
        does not use a single deletion flag. Instead the PIC is replaced by the
        special string "DELETED" in the RDB field as well as in the first TIFF
        page (the stored PIC on the second TIFF page is left intact so the
        value can be recovered).
        This method provides a simple API to determine the deletion state. The
        main part is a user defined condition.
        """
        assert (operator in (Source.OR, Source.AND))

        is_cdb_deleted = None
        if cdb:
            cdb_form = self.batch.form(self.form_index)
            is_cdb_deleted = cdb_form.is_deleted()
        is_ibf_deleted = None
        if ibf:
            image_data = self.ibf.image_entries[self.form_index]
            ibf_rec_pic = image_data.rec.codnr
            is_ibf_deleted = (ibf_rec_pic == 'DELETED')
        if operator == Source.AND:
            is_deleted = (is_cdb_deleted and is_ibf_deleted)
        else:
            is_deleted = (is_cdb_deleted or is_ibf_deleted)
        # not (not ...) to ensure we always return a bool (not None)
        return not (not is_deleted)

    def pic(self):
        image_data = self.ibf.image_entries[self.form_index]
        ibf_rec_pic = image_data.rec.codnr
        if ibf_rec_pic != 'DELETED':
            return ibf_rec_pic

        th = self.batch.tiff_handler(self.form_index)
        ibf_long_pic = th.long_data2.rec.page_name
        return ibf_long_pic
