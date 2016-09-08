# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from pythonic_testcase import *

from sqlalchemy import and_

from ddc.storage import Batch, DataBunch
from ddc.storage.ask import create_ask
from ddc.storage.cdb import create_cdb_with_dummy_data
from ddc.storage.ibf import create_ibf
from ddc.storage.sqlite import create_sqlite_db
from ddc.storage.utils import DELETE


class DBFormTest(PythonicTestCase):
    def test_can_store_and_retrieve_form_settings(self):
        batch = self._create_batch(nr_forms=2)
        db = batch.db
        key = 'foo'
        form = batch.db_form(0)
        form.store_setting(key, '42') # new setting
        form1 = batch.db_form(1)
        form1.store_setting(key, '99') # unrelated setting for other form

        FormData = db.model.FormData
        c = and_(
            FormData.key == key,
            FormData.form_index == 0,
        )
        setting = db.session.query(FormData).filter(c).one()
        assert_equals('42', setting.value,
            message='initial value was not stored in the database')
        assert_equals('42', form.get_setting(key),
            message='error while retrieving setting')

        form.store_setting(key, '21')
        assert_equals('21', form.get_setting(key),
            message='should be able to retrieve updated (pre-existing) setting')

    def test_can_delete_form_settings(self):
        batch = self._create_batch(nr_forms=2)
        key = 'foo'
        form = batch.db_form(0)
        form1 = batch.db_form(1)
        form1.store_setting(key, '99') # unrelated setting for other form
        assert_none(form.get_setting(key),
            message='should return None for non-existing setting')

        form.store_setting(key, value=DELETE)
        assert_none(form.get_setting(key),
            message='deleting a non-existing setting should have no effect')
        assert_equals('99', form1.get_setting(key), message='unrelated value should be kept')

        form.store_setting(key, '21')
        assert_equals('21', form.get_setting(key), message='ensure value was set')

        form.store_setting(key, value=DELETE)
        assert_none(form.get_setting(key), message='setting should be gone now')

    # --- helpers -------------------------------------------------------------
    def _create_batch(self, *, nr_forms=1, tasks=(), ignored_warnings=(), model=None):
        databunch = DataBunch(
            cdb=create_cdb_with_dummy_data(nr_forms=nr_forms),
            ibf=create_ibf(nr_images=nr_forms),
            db=create_sqlite_db(tasks=tasks, ignored_warnings=ignored_warnings, model=model),
            ask=create_ask(),
        )
        batch = Batch.init_from_bunch(databunch, create_new_db=False)
        return batch
