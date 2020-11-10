# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import os

from pythonic_testcase import *
from schwarz.fakefs_helpers import TempFS

from srw.rdblib import TaskType
from .. import create_sqlite_db, DBVersion, SQLiteDB



class SQLiteDBTest(PythonicTestCase):
    def setUp(self):
        self.fs = TempFS.set_up(test=self)

    def test_can_create_new_database(self):
        db_filename = os.path.join(self.fs.root, 'foo.db')
        assert_false(os.path.exists(db_filename))
        db = SQLiteDB.create_new_db(db_filename, create_file=True)
        assert_true(os.path.exists(db_filename))
        # close all open files - so we can open the db again
        db.close()

        with assert_not_raises():
            db = SQLiteDB.init_with_file(db_filename)
        # close all open files - otherwise Windows won't be able to remove
        # the temp dir
        db.close()

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
        db_filename = os.path.join(self.fs.root, 'foo.db')
        db = SQLiteDB.create_new_db(db_filename, create_file=True)
        engine = db.session.bind
        connection = db.session.connection()
        assert_true(engine.dialect.has_table(connection, 'dbversion'))

        db_version = db.query(DBVersion).one()
        assert_equals('v201609', db_version.version_id)
        # close all open files - otherwise Windows won't be able to remove
        # the temp dir
        db.close()

    def test_rejects_opening_db_without_dbversion_table(self):
        db_filename = os.path.join(self.fs.root, 'foo.db')
        db = SQLiteDB.create_new_db(db_filename, create_file=True)
        engine = db.session.bind
        version_table = DBVersion.__table__
        version_table.drop(engine, checkfirst=True)
        connection = db.session.connection()
        assert_false(engine.dialect.has_table(connection, version_table.name))
        # close all open files - otherwise Windows won't be able to remove
        # the temp dir
        db.close()

        with assert_raises(ValueError):
            SQLiteDB.init_with_file(db_filename, create=False)

    def test_rejects_opening_db_with_unknown_dbversion(self):
        db_filename = os.path.join(self.fs.root, 'foo.db')
        db = SQLiteDB.create_new_db(db_filename, create_file=True)
        db_version = db.query(DBVersion).one()
        db_version.version_id = u'unknown'
        db.commit()
        # close all open files - otherwise Windows won't be able to remove
        # the temp dir
        db.close()

        with assert_raises(ValueError):
            SQLiteDB.init_with_file(db_filename, create=False)
