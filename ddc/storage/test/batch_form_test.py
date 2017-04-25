# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from pythonic_testcase import *

from ddc.storage.batch_form import Source
from ddc.storage.testhelpers import batch_with_pic_forms
from ddc.tool.cdb_collection import CDB_Collection


class BatchFormTest(PythonicTestCase):
    def test_can_retrieve_pic_for_form(self):
        pic1 = '12345600100024'
        pic2 = '12345600114024'
        batch = batch_with_pic_forms([pic1, pic2])
        assert_equals(pic1, batch.batch_form(0).pic())
        assert_equals(pic2, batch.batch_form(1).pic())

    def test_can_retrieve_deletion_state(self):
        pic1 = '12345600100024'
        batch = batch_with_pic_forms([pic1])
        form = batch.batch_form(0)
        assert_false(form.is_deleted())

        # LATER: CDB_Collection should not be necessary, this should be possible
        # by just using the BatchForm...
        cdb_collection = CDB_Collection(batch)
        cdb_form = cdb_collection.forms[0]
        cdb_form.delete()
        assert_true(form.is_deleted())
        assert_true(form.is_deleted(cdb=True, ibf=False))
        assert_true(form.is_deleted(cdb=False, ibf=True))

        # This can happen sometimes in the Walther OCR process: E.g. due to a
        # machine error the image was marked as "deleted" when scanning. In that
        # case the RDP PIC fields are empty but the IBF correctly says
        # "DELETED". Our ".is_deleted()" should be able to tell the difference.
        rdb_form = batch.cdb.forms[0]
        rdb_form.form_header.update_rec(
            imprint_line_long='',
            imprint_line_short=''
        )
        # This happens also in the ".delete()" method even though it is known
        # to be hackish (should only be done by ".commit()")
        cdb_form.write_back()
        assert_true(form.is_deleted())
        assert_true(form.is_deleted(cdb=False, ibf=True))
        assert_false(form.is_deleted(cdb=True, ibf=False))
        assert_false(form.is_deleted(cdb=True, ibf=True, operator=Source.AND))
