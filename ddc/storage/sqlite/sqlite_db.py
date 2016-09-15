# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ddc.lib.log_proxy import l_
from . import model as db_schema
from .dbform import DBForm
from .model import get_model
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
    def __init__(self, metadata, session, model, log=None):
        self.metadata = metadata
        self.session = session
        self.model = model
        self.log = l_(log)

    @classmethod
    def create_new_db(cls, filename='', *, create_file, log=None, model=None):
        db = cls.init_with_file(filename, create=create_file, log=log, model=model)
        engine = db.session.bind
        db.metadata.create_all(bind=engine)
        # stamp with alembic
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
        log_filename = filename if filename else '[in memory]'
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
        log.info('opened SQlite db "%s"', log_filename)
        return SQLiteDB(metadata, session, model_, log=log)

    # --- connection handling -------------------------------------------------
    def is_dirty(self):
        # seems like it is quite complicated to find out as SQLAlchemy was not
        # built for that: http://stackoverflow.com/q/16256777/138526
        # so let's always do a commit and let SQLAlchemy/SQLite figure out the
        # rest.
        return True

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
    abort = rollback

    # TODO: Do we need close/save?
    def close(self):
        self.session.rollback()
        self.session.close()

    save = commit

    # --- querying ------------------------------------------------------------
    def __getattr__(self, key):
        if key in self.model:
            return self.model[key]
        raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, key))

    def query(self, orm_class):
        return self.session.query(orm_class)
