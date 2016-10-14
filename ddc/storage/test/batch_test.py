# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import os

from pythonic_testcase import *

from ddc.storage import guess_path, Batch, DataBunch, TaskStatus, TaskType
from ddc.storage.ask import create_ask
from ddc.storage.cdb import create_cdb_with_dummy_data
from ddc.storage.ibf import create_ibf
from ddc.storage.sqlite import create_sqlite_db, db_schema, get_model
from ddc.storage.testhelpers import batch_with_pic_forms, use_tempdir
from ddc.storage.utils import DELETE

class BatchTest(PythonicTestCase):
    def test_can_initialize_batch_without_real_files(self):
        batch = self._create_batch(tasks=())
        assert_isinstance(batch, Batch)

    def test_can_create_new_db_when_initializing_with_bunch(self):
        nr_forms = 2
        with use_tempdir() as temp_dir:
            cdb_path = os.path.join(temp_dir, '00042100.CDB')
            ibf_path = guess_path(cdb_path, type_='ibf')
            create_cdb_with_dummy_data(nr_forms=nr_forms, filename=cdb_path)
            create_ibf(nr_images=nr_forms, filename=ibf_path, create_directory=True)
            bunch = DataBunch(cdb_path, ibf_path, db=None, ask=None)

            batch = Batch.init_from_bunch(bunch, create_persistent_db=True, access='write')
            bunch = batch.bunch
            assert_not_none(bunch.db)
            assert_true(os.path.exists(bunch.db))
            batch.close()

            with assert_not_raises(OSError):
                Batch.init_from_bunch(bunch, create_persistent_db=False)

    def test_can_add_tasks_via_batch(self):
        model = get_model(db_schema.LATEST)
        batch = self._create_batch(tasks=(), model=model)
        assert_length(0, batch.tasks())
        db_form = batch.db_form(0)
        db_form.add_task(type_=TaskType.FORM_VALIDATION, status=TaskStatus.NEW)
        assert_length(1, batch.tasks())

    def test_can_retrieve_only_selected_tasks(self):
        model = get_model(db_schema.LATEST)
        new_task = model.Task(0, TaskType.FORM_VALIDATION, status=TaskStatus.NEW)
        closed_task = model.Task(0, TaskType.VERIFICATION, status=TaskStatus.CLOSED)
        verification_task = model.Task(0, TaskType.VERIFICATION, status=TaskStatus.CLOSED)
        second_form_task = model.Task(1, TaskType.FORM_VALIDATION, status=TaskStatus.CLOSED)
        tasks = (new_task, closed_task, verification_task, second_form_task)
        batch = self._create_batch(tasks=tasks, model=model)

        assert_length(4, batch.tasks())
        assert_length(1, batch.tasks(status=TaskStatus.NEW))
        assert_length(3, batch.tasks(status=TaskStatus.CLOSED))
        assert_length(2, batch.tasks(type_=TaskType.VERIFICATION))
        assert_length(2, batch.tasks(type_=TaskType.FORM_VALIDATION))
        assert_length(3, batch.db_form(0).tasks())
        assert_length(1, batch.db_form(1).tasks())

    def test_new_tasks(self):
        model = get_model(db_schema.LATEST)
        new_task = model.Task(0, TaskType.FORM_VALIDATION, status=TaskStatus.NEW)
        closed_task = model.Task(1, TaskType.VERIFICATION, status=TaskStatus.CLOSED)
        batch = self._create_batch(tasks=(new_task, closed_task), model=model)
        assert_length(2, batch.tasks())

        assert_length(1, batch.new_tasks())
        assert_length(0, batch.new_tasks(TaskType.VERIFICATION))

    def test_can_retrieve_pic_for_form(self):
        pic1 = '12345600100024'
        pic2 = '12345600114024'
        batch = batch_with_pic_forms([pic1, pic2])
        assert_equals(pic1, batch.pic_for_form(0))
        assert_equals(pic2, batch.pic_for_form(1))

    def test_can_retrieve_ignored_warnings(self):
        ignore_key = ('FOO', 'some_error', '21')
        ignored_warnings = ( (1, ) + ignore_key, )
        batch = self._create_batch(ignored_warnings=ignored_warnings)
        assert_length(0, batch.db_form(0).ignored_warnings())
        assert_equals((ignore_key,), batch.db_form(1).ignored_warnings(as_ignore_key=True))

    def test_can_store_ignored_warnings(self):
        batch = self._create_batch()
        db_form0 = batch.db_form(0)
        assert_length(0, db_form0.ignored_warnings())

        field_name = 'FOO'
        error_key = 'someerror'
        field_value = '42'
        db_form0.add_ignored_warning(field_name, error_key, field_value)

        ignore_key = (field_name, error_key, field_value)
        assert_equals((ignore_key,), db_form0.ignored_warnings(as_ignore_key=True))
        assert_length(0, batch.db_form(1).ignored_warnings())

        db_form0.add_ignored_warning(field_name, error_key, field_value)
        assert_length(1, db_form0.ignored_warnings(),
            message='does not store duplicate ignored warnings')

    def test_can_store_and_retrieve_batch_settings(self):
        batch = self._create_batch()
        key = 'foo'
        batch.store_setting(key, '42') # new setting

        db = batch.db
        BatchData = db.model.BatchData
        setting = db.session.query(BatchData).filter(BatchData.key == key).one()
        assert_equals('42', setting.value,
            message='initial value was not stored in the database')
        assert_equals('42', batch.get_setting(key),
            message='error while retrieving setting')

        batch.store_setting(key, '21')
        assert_equals('21', batch.get_setting(key),
            message='should be able to retrieve updated (pre-existing) setting')

    def test_can_delete_batch_settings(self):
        batch = self._create_batch()
        key = 'foo'
        assert_none(batch.get_setting(key),
            message='should return None for non-existing setting')

        batch.store_setting(key, value=DELETE)
        assert_none(batch.get_setting(key),
            message='deleting a non-existing setting should have no effect')

        batch.store_setting(key, '21')
        assert_equals('21', batch.get_setting(key), message='ensure value was set')

        batch.store_setting(key, value=DELETE)
        assert_none(batch.get_setting(key), message='setting should be gone now')

    def test_batch_commit_also_stores_cdb_data(self):
        nr_forms = 2
        with use_tempdir() as temp_dir:
            cdb_path = os.path.join(temp_dir, '00042100.CDB')
            ibf_path = guess_path(cdb_path, type_='ibf')
            create_cdb_with_dummy_data(nr_forms=nr_forms, filename=cdb_path)
            create_ibf(nr_images=nr_forms, filename=ibf_path, create_directory=True)
            bunch = DataBunch(cdb_path, ibf_path, db=None, ask=None)

            batch = Batch.init_from_bunch(bunch, create_persistent_db=False, access='write')
            form = batch.form(0)
            field_name = tuple(form.fields)[0]
            previous_value = form.fields[field_name].value
            new_value = 'foobar'
            form.fields[field_name].value = new_value
            assert_not_equals(previous_value, new_value,
                message='must set a different value so we test the real thing')
            batch.commit()
            batch.close()

            batch = Batch.init_from_bunch(bunch, create_persistent_db=False, access='write')
            form = batch.form(0)
            assert_equals(new_value, form.fields[field_name].value)

    # --- helpers -------------------------------------------------------------
    def _create_batch(self, *, nr_forms=1, tasks=(), ignored_warnings=(), model=None):
        databunch = DataBunch(
            cdb=create_cdb_with_dummy_data(nr_forms=nr_forms),
            ibf=create_ibf(nr_images=nr_forms),
            db=create_sqlite_db(tasks=tasks, ignored_warnings=ignored_warnings, model=model),
            ask=create_ask(),
        )
        batch = Batch.init_from_bunch(databunch, create_persistent_db=False)
        return batch

