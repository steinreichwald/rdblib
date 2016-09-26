# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from pythonic_testcase import *

from ddc.storage.sqlite import create_sqlite_db
from ddc.storage.task import TaskType
from ddc.storage.sqlite.sqlite_db import SQLiteDB


class SQLiteDBTest(PythonicTestCase):
    def test_can_track_dirty_state(self):
        db = create_sqlite_db()
        session = db.session
        Task = db.model.Task

        assert_false(db.is_dirty(), message='initial db should be clean')

        task = Task(form_index=0, type_=TaskType.VERIFICATION)
        session.add(task)
        assert_true(db.is_dirty())

        session.flush()
        assert_true(db.is_dirty(),
            message='should be dirty even after flushing a session')

        session.commit()
        assert_false(db.is_dirty(), message='db must be clean after committing')

        task = session.query(Task).first()
        assert_false(db.is_dirty())
        task.status = 'bar'
        assert_true(db.is_dirty())

        session.delete(task)
        assert_true(db.is_dirty(), message='pending delete should mark session as dirty')

        session.rollback()
        assert_false(db.is_dirty())

        session.flush()
        assert_false(db.is_dirty(),
            message='empty flush should not mark session as dirty')


    def test_new_db_should_be_dirty(self):
        db = SQLiteDB.create_new_db(create_file=False)
        assert_false(db.is_dirty())

