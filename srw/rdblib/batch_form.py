# -*- coding: utf-8 -*-

import enum


__all__ = ['BatchForm']

DELETION_MARKER = 'DELETED'

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
            is_ibf_deleted = (ibf_rec_pic == DELETION_MARKER)
        if operator == Source.AND:
            is_deleted = (is_cdb_deleted and is_ibf_deleted)
        else:
            is_deleted = (is_cdb_deleted or is_ibf_deleted)
        # not (not ...) to ensure we always return a bool (not None)
        return not (not is_deleted)

    def delete(self):
        self._set_deletion_state(True)

    def _set_deletion_state(self, set_as_deleted):
        cdb_form = self.batch.cdb.forms[self.form_index]
        ibf_data = self.ibf.image_entries[self.form_index]
        tiff_handler = self.batch.tiff_handler(self.form_index)
        if set_as_deleted:
            repl_str = DELETION_MARKER
        else:
            # Note: long_data2 is the second version of the tiff header.
            # This is never written, but kept as a backup for un-deleting.
            repl_str = tiff_handler.long_data2.rec.page_name
        #
        # First, change the data of the form header.
        cdb_form.form_header.update_rec(
            imprint_line_long = repl_str,
            imprint_line_short = repl_str)
        #
        # Second, change the data of the tiff header.
        #
        # Note that we update only the first copy of the tiff structure (page 1).
        # The second copy will always remain unchanged, because the old software
        # ignores that. Therefore, the second copy is used to restore a "deleted"
        # scan.
        #
        # This line puts the new record data into the tiff header struc (in memory).
        tiff_handler.long_data.update_rec(page_name = repl_str)
        # This line also patches the new data into the tiff structure (in memory).
        ibf_data.update_rec(codnr = repl_str)
        #
        # Upto here, no data was physically written.
        # We do that now. Actually, that should logically be a transaction,
        # but we ignore this for CDB/IBF.
        #
        # First, we actualize the form data:
        # - move the data in memory back to the structure on disk.
        cdb_form.write_back()
        #
        # Then we update the index info in the IBF:
        self.ibf.update_entry(ibf_data)
        #
        # And as the last step, we also ask the tiff handler to write its data to disk.
        tiff_handler.update()

    def pic(self):
        image_data = self.ibf.image_entries[self.form_index]
        ibf_rec_pic = image_data.rec.codnr
        if ibf_rec_pic != DELETION_MARKER:
            return ibf_rec_pic

        th = self.batch.tiff_handler(self.form_index)
        ibf_long_pic = th.long_data2.rec.page_name
        return ibf_long_pic
