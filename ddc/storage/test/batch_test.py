# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from pythonic_testcase import *

from ddc.storage import Batch, DataBunch, Task, TaskStatus, TaskType
from ddc.storage.ask import create_ask
from ddc.storage.cdb import create_cdb_with_dummy_data
from ddc.storage.durus_ import create_durus_fixture
from ddc.storage.ibf import create_ibf
from ddc.storage.testhelpers import (
    batch_with_pic_forms, set_durus_loglevel, silence_durus_logging,
)


class BatchTest(PythonicTestCase):
    def setUp(self):
        super(BatchTest, self).setUp()
        self._previous_loglevel = silence_durus_logging()

    def tearDown(self):
        set_durus_loglevel(self._previous_loglevel)
        super(BatchTest, self).tearDown()

    def test_can_initialize_batch_without_real_files(self):
        batch = self._create_batch(tasks=())
        assert_isinstance(batch, Batch)

    def test_can_add_tasks_via_batch(self):
        batch = self._create_batch(tasks=())
        assert_length(0, batch.tasks())
        new_task = Task(0, TaskType.FORM_VALIDATION, status=TaskStatus.NEW)
        batch.tasks().append(new_task)
        assert_length(1, batch.tasks())

    def test_can_retrieve_only_selected_tasks(self):
        new_task = Task(0, TaskType.FORM_VALIDATION, status=TaskStatus.NEW)
        closed_task = Task(0, TaskType.VERIFICATION, status=TaskStatus.CLOSED)
        verification_task = Task(0, TaskType.VERIFICATION, status=TaskStatus.CLOSED)
        second_form_task = Task(1, TaskType.FORM_VALIDATION, status=TaskStatus.CLOSED)
        tasks = (new_task, closed_task, verification_task, second_form_task)
        batch = self._create_batch(tasks=tasks)

        assert_length(4, batch.tasks())
        assert_length(1, batch.tasks(status=TaskStatus.NEW))
        assert_length(3, batch.tasks(status=TaskStatus.CLOSED))
        assert_length(2, batch.tasks(type_=TaskType.VERIFICATION))
        assert_length(2, batch.tasks(type_=TaskType.FORM_VALIDATION))
        assert_length(3, batch.tasks(form_position=0))
        assert_length(1, batch.tasks(form_position=1))

    def test_new_tasks(self):
        new_task = Task(0, TaskType.FORM_VALIDATION, status=TaskStatus.NEW)
        closed_task = Task(1, TaskType.VERIFICATION, status=TaskStatus.CLOSED)
        batch = self._create_batch(tasks=(new_task, closed_task))
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
        assert_length(0, batch.ignored_warnings(form_index=0))
        assert_equals((ignore_key,), batch.ignored_warnings(form_index=1))

    def test_can_store_ignored_warnings(self):
        batch = self._create_batch()
        assert_length(0, batch.ignored_warnings(form_index=0))

        field_name = 'FOO'
        error_key = 'someerror'
        field_value = '42'
        ignore_key = (field_name, error_key, field_value)
        batch.store_ignored_warning(0, *ignore_key)

        assert_equals((ignore_key,), batch.ignored_warnings(form_index=0))
        assert_length(0, batch.ignored_warnings(form_index=1))

        batch.store_ignored_warning(0, *ignore_key)
        assert_length(1, batch.ignored_warnings(form_index=0),
            message='does not store duplicate ignored warnings')

    # --- helpers -------------------------------------------------------------
    def _create_batch(self, *, nr_forms=1, tasks=(), ignored_warnings=()):
        databunch = DataBunch(
            cdb=create_cdb_with_dummy_data(nr_forms=nr_forms),
            ibf=create_ibf(nr_images=nr_forms),
            durus=create_durus_fixture(tasks=tasks, ignored_warnings=ignored_warnings),
            ask=create_ask(),
        )
        batch = Batch.init_from_bunch(databunch, create_new_durus=False)
        return batch

