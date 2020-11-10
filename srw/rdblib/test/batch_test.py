# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import hashlib
import os

from pythonic_testcase import *
from schwarz.fakefs_helpers import TempFS

from srw.rdblib import assemble_new_path, guess_path, DataBunch
from srw.rdblib.cdb import create_cdb_with_dummy_data
from srw.rdblib.ibf import create_ibf
from .. import TaskStatus, TaskType
from ..batch import Batch
from ..sqlite import create_sqlite_db, db_schema, get_model, DELETE


class BatchTest(PythonicTestCase):
    def setUp(self):
        self.fs = TempFS.set_up(test=self)

    def test_can_initialize_batch_without_real_files(self):
        batch = self._create_batch(tasks=())
        assert_isinstance(batch, Batch)

    def test_can_create_new_db_when_initializing_with_bunch(self):
        cdb_path = os.path.join(self.fs.root, '00042100.CDB')
        batch = self._create_cdbibf_batch(cdb_path, nr_forms=2, create_persistent_db=True)

        bunch = batch.bunch
        assert_not_none(bunch.db)
        assert_true(os.path.exists(bunch.db))
        batch.close()

        with assert_not_raises(OSError):
            batch = Batch.init_from_bunch(bunch, create_persistent_db=False)
        # close all open files - otherwise Windows won't be able to remove
        # the temp dir
        batch.close()

    def test_can_rename_batch(self):
        canary_value = '00031526'
        rdb_path = os.path.join(self.fs.root, '00042100.RDB')
        batch = self._create_cdbibf_batch(rdb_path, nr_forms=2, form0_data={'PZN_1': canary_value})
        id_formbatch = id(batch.cdb)

        batch.rename_xdb(to='CDB')
        cdb_path = os.path.splitext(rdb_path)[0] + '.CDB'
        assert_not_equals(id_formbatch, id(batch.cdb))
        assert_equals(cdb_path, batch.bunch.cdb)
        assert_true(os.path.exists(cdb_path))
        assert_false(os.path.exists(rdb_path))
        assert_equals(canary_value, batch.form(0)['PZN_1'].value)

        # close all open files - otherwise Windows won't be able to remove
        # the temp dir
        batch.close()

    def test_fails_rename_if_target_file_already_exists(self):
        rdb_path = os.path.join(self.fs.root, '00042100.RDB')
        cdb_path = rdb_path.replace('.RDB', '.CDB')
        batch = self._create_cdbibf_batch(rdb_path, nr_forms=2)
        with open(cdb_path, 'wb') as fp:
            fp.write(b'should be kept')

        with assert_raises(FileExistsError):
            batch.rename_xdb(to='CDB')
        assert_true(os.path.exists(rdb_path))
        assert_true(os.path.exists(cdb_path))
        # close all open files - otherwise Windows won't be able to remove
        # the temp dir
        batch.close()

    def test_can_rename_and_move_cdb(self):
        canary_value = '00031526'
        rdb_path = os.path.join(self.fs.root, 'subdir', '00042100.RDB')
        batch = self._create_cdbibf_batch(rdb_path, nr_forms=2, form0_data={'PZN_1': canary_value})
        id_formbatch = id(batch.cdb)

        target_dir = os.path.join(self.fs.root, 'cdb_dir')
        assert_false(os.path.exists(target_dir),
            message='rename_xdb() should create the target dir if necessary')
        batch.rename_xdb(to='CDB', target_dir=target_dir)
        cdb_path = os.path.join(target_dir, '00042100.CDB')
        assert_false(os.path.exists(rdb_path))
        assert_not_equals(id_formbatch, id(batch.cdb))
        assert_equals(cdb_path, batch.bunch.cdb)
        assert_true(os.path.exists(cdb_path))
        assert_equals(target_dir, os.path.dirname(cdb_path))
        assert_equals(canary_value, batch.form(0)['PZN_1'].value)

        # close all open files - otherwise Windows won't be able to remove
        # the temp dir
        batch.close()

    def test_can_backup_original_file_before_renaming_cdb(self):
        canary_value = '00031526'
        rdb_path = os.path.join(self.fs.root, '00042100.RDB')
        batch = self._create_cdbibf_batch(rdb_path, nr_forms=2, form0_data={'PZN_1': canary_value})
        cdb_hash = hashlib.md5(batch.cdb.filecontent).hexdigest()

        backup_dir = os.path.join(self.fs.root, 'backup')
        batch.rename_xdb(to='CDB', backup_dir=backup_dir)
        cdb_path = os.path.join(self.fs.root, '00042100.CDB')
        assert_false(os.path.exists(rdb_path))
        assert_true(os.path.exists(cdb_path))

        rdb_backup_path = assemble_new_path(rdb_path, new_dir=backup_dir, new_extension='RDB.BAK')
        assert_true(os.path.exists(rdb_backup_path))
        with open(rdb_backup_path, 'rb') as fp:
            backup_hash = hashlib.md5(fp.read()).hexdigest()
        assert_equals(cdb_hash, backup_hash)

        # ensure the code does not overwrite backup files
        batch.rename_xdb(to='RDB')
        batch.rename_xdb(to='CDB', backup_dir=backup_dir)
        backup1_path = rdb_backup_path + '.1'
        assert_true(os.path.exists(backup1_path))

        # close all open files - otherwise Windows won't be able to remove
        # the temp dir
        batch.close()

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
        field_names = ('FOO', 'BAR')
        cdb_path = os.path.join(self.fs.root, '00042100.CDB')
        ibf_path = guess_path(cdb_path, type_='ibf')
        create_cdb_with_dummy_data(nr_forms=nr_forms, filename=cdb_path, field_names=field_names)
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
        # close all open files - otherwise Windows won't be able to remove
        # the temp dir
        batch.close()

    # --- helpers -------------------------------------------------------------

    def _create_cdbibf_batch(self, cdb_path, nr_forms=1, form0_data=None, create_persistent_db=False):
        field_names = ('FOO', ) + (tuple(form0_data or ()))
        cdb_dir = os.path.dirname(cdb_path)
        os.makedirs(cdb_dir, exist_ok=True)
        ibf_path = guess_path(cdb_path, type_='ibf')
        create_cdb_with_dummy_data(nr_forms=nr_forms, filename=cdb_path, field_names=field_names)
        create_ibf(nr_images=nr_forms, filename=ibf_path, create_directory=True)
        bunch = DataBunch(cdb_path, ibf_path, db=None, ask=None)
        batch = Batch.init_from_bunch(
            bunch,
            create_persistent_db=create_persistent_db,
            access='write',
        )
        if form0_data:
            for field_name, value in form0_data.items():
                batch.form(0)[field_name].value = value
            batch.cdb.commit()
        return batch

    def _create_batch(self, *, nr_forms=1, tasks=(), ignored_warnings=(), model=None):
        field_names = ('FOO',)
        databunch = DataBunch(
            cdb=create_cdb_with_dummy_data(nr_forms=nr_forms, field_names=field_names),
            ibf=create_ibf(nr_images=nr_forms),
            db=create_sqlite_db(tasks=tasks, ignored_warnings=ignored_warnings, model=model),
            ask=None,
        )
        batch = Batch.init_from_bunch(databunch, create_persistent_db=False)
        return batch

