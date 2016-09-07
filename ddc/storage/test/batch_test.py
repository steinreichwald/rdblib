# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from pythonic_testcase import *

from ddc.storage import Batch, DataBunch, TaskStatus, TaskType
from ddc.storage.ask import create_ask
from ddc.storage.cdb import create_cdb_with_dummy_data
from ddc.storage.sqlite import create_sqlite_db, db_schema, get_model
from ddc.storage.ibf import create_ibf
from ddc.storage.testhelpers import batch_with_pic_forms

class BatchTest(PythonicTestCase):
    def test_can_initialize_batch_without_real_files(self):
        batch = self._create_batch(tasks=())
        assert_isinstance(batch, Batch)

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

