# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals


import os

from pythonic_testcase import *

from ddc.storage.task import TaskType
from ddc.storage.testhelpers import use_tempdir
from ddc.storage import create_sqlite_db, DBVersion, SQLiteDB


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

    def test_new_db_should_be_clean(self):
        db = SQLiteDB.create_new_db(create_file=False)
        assert_false(db.is_dirty())

    def test_stores_current_db_version_when_creating_a_new_database(self):
        with use_tempdir() as temp_dir:
            db_filename = os.path.join(temp_dir, 'foo.db')
            db = SQLiteDB.create_new_db(db_filename, create_file=True)
            engine = db.session.bind
            connection = db.session.connection()
            assert_true(engine.dialect.has_table(connection, 'dbversion'))

            db_version = db.query(DBVersion).one()
            assert_equals('v201609', db_version.version_id)

    def test_rejects_opening_db_without_dbversion_table(self):
        with use_tempdir() as temp_dir:
            db_filename = os.path.join(temp_dir, 'foo.db')
            db = SQLiteDB.create_new_db(db_filename, create_file=True)
            engine = db.session.bind
            version_table = DBVersion.__table__
            version_table.drop(engine, checkfirst=True)
            connection = db.session.connection()
            assert_false(engine.dialect.has_table(connection, version_table.name))

            with assert_raises(ValueError):
                SQLiteDB.init_with_file(db_filename, create=False)

    def test_rejects_opening_db_with_unknown_dbversion(self):
        with use_tempdir() as temp_dir:
            db_filename = os.path.join(temp_dir, 'foo.db')
            db = SQLiteDB.create_new_db(db_filename, create_file=True)
            db_version = db.query(DBVersion).one()
            db_version.version_id = u'unknown'
            db.commit()

            with assert_raises(ValueError):
                SQLiteDB.init_with_file(db_filename, create=False)
