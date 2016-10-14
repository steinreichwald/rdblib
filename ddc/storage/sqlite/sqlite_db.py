# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from ddc.lib.log_proxy import l_
from . import model as db_schema
from .dbform import DBForm
from .model import get_model, DBVersion
from ..utils import DELETE as DELETE_


__all__ = ['create_sqlite_db', 'SQLiteDB']

def create_sqlite_db(tasks=(), ignored_warnings=(), filename='', model=None):
    create_file = not (not filename)
    db = SQLiteDB.create_new_db(filename, create_file=create_file, model=model)
    for task in tasks:
        db.session.add(task)
    for warning in ignored_warnings:
        if isinstance(warning, tuple):
            form_index, field_name, error_key, field_value = warning
            db_form = DBForm(db.session, form_index, db.model)
            warning = db_form.add_ignored_warning(field_name, error_key, field_value)
        db.session.add(warning)
    db.commit()
    return db


class SQLiteDB(object):
    DELETE = DELETE_
    def __init__(self, metadata, session, model, *, log=None, ignore_db_version=False):
        self.metadata = metadata
        self.session = session
        self._engine = self.session.bind
        self.model = model
        self.log = l_(log)
        if not ignore_db_version:
            self._ensure_db_version_matches_model(self.session, self.model, self.log)

        # for performance reasons SQLAlchemy does not track if a session needs
        # a DB change (at least there is no API) so we have to do the recording
        # ourself using events (also see http://stackoverflow.com/q/16256777/138526)
        self._was_flushed = False
        self._listeners = [
            ('after_flush', self._on_flush),
            ('after_commit', self._on_commit),
        ]
        self._register_listeners()

    def _ensure_db_version_matches_model(self, session, model, log):
        connection = session.connection()
        version_table_name = DBVersion.__table__.name
        if not self._engine.dialect.has_table(connection, version_table_name):
            msg = 'DB version table "%s" does not exist!' % version_table_name
            log.error(msg)
            raise ValueError(msg)
        db_version = session.query(DBVersion).first()
        if db_version.version_id != model.id:
            msg = 'DB version mismatch %s (DB) vs. %s (model)' % (db_version.version_id, model.id)
            log.error(msg)
            raise ValueError(msg)

    @classmethod
    def create_new_db(cls, filename='', *, create_file, log=None, model=None):
        db = cls.init_with_file(filename, create=True, log=log, model=model)
        engine = db.session.bind
        DBVersion.metadata.create_all(bind=engine)
        db.metadata.create_all(bind=engine)
        db.session.add(DBVersion(version_id=db.model.id))
        db.commit()
        return db

    @classmethod
    def init_with_file(cls, filename, *, create=False, log=None, model=None):
        log = l_(log)
        model_ = model or get_model(db_schema.LATEST)

        if filename:
            # Of course these conditions are racy but they will likely catch
            # most errors in using this function.
            # Also the "create" parameter transports the developer's intention
            # so we can optimize the implementation later.
            if create and os.path.exists(filename):
                raise IOError('DB file "%s" already exists' % filename)
            elif (not create) and (not os.path.exists(filename)):
                raise IOError('DB file "%s" does not exist' % filename)
        logged_filename = filename if filename else '[in memory]'
        if filename:
            path_uri = os.path.abspath(filename)
        else:
            path_uri = ''
        db_uri = 'sqlite:///' + path_uri
        echo = False
        # echo = 'debug' # for full debugging output (including results
        engine = create_engine(db_uri, echo=echo)
        metadata = model_.metadata
        session = Session(bind=engine)

        log.info('opened SQlite db "%s"', logged_filename)
        return SQLiteDB(metadata, session, model_, log=log, ignore_db_version=create)

    # --- connection handling -------------------------------------------------
    def is_dirty(self):
        if self._was_flushed:
            print('session was flushed')
            return True
        elif self.session.new or self.session.deleted:
            return True
        has_modified_items = len([x for x in self.session.dirty if self.session.is_modified(x)]) > 0
        if has_modified_items:
            return True
        return False

    # only meant for testing
    def _new_session(self):
        # At least one test uses a SQLiteDB instance which is "re-used" after
        # close so it does not need to use real files. Provide a way for such
        # tests to reinitialize the DB session while catching errorneous
        # access to closed sessions.
        assert self.session is None
        self.session = Session(bind=self._engine)
        self._register_listeners()

    def _register_listeners(self):
        for key in self._listeners:
            event.listen(self.session, *key)

    def _on_flush(self, session, flush_context):
        self._was_flushed = True
        assert session == self.session

    def _on_commit(self, session):
        self._was_flushed = False
        assert session == self.session

    def commit(self):
        assert (self.session is not None)
        self.session.commit()
        self._was_flushed = False

    def rollback(self):
        assert (self.session is not None)
        self.session.rollback()
    abort = rollback

    def close(self):
        assert (self.session is not None)
        self.session.rollback()
        for key in self._listeners:
            event.remove(self.session, *key)
        self.session.close()
        self.session = None

    save = commit

    # --- querying ------------------------------------------------------------
    def __getattr__(self, key):
        if key in self.model:
            return self.model[key]
        raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, key))

    def query(self, orm_class):
        return self.session.query(orm_class)
