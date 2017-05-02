# -*- coding: utf-8 -*-
"""
The basic idea is that we always need a triple to access all relevant information.
  1. CDB files for extracted text data
  2. IBF for actual images (scans)
  3. SQLite DB for meta data

DataBunch represents the path information for that triple (so no file system
access or active databases required). The Batch is the main abstraction which
hides all implementation details (as much as possible/sensible).
"""

from __future__ import division, absolute_import, print_function, unicode_literals

from sqlalchemy import and_

from ddc.lib.log_proxy import l_
from .batch_form import BatchForm
from .ibf import ImageBatch
from .ibf.tiff_handler import TiffHandler
from .paths import guess_path, simple_bunch, DataBunch
from .sqlite import get_or_add, DBForm, SQLiteDB
from .task import TaskStatus, TaskType
from .utils import DELETE


__all__ = ['Batch']

class Batch(object):
    def __init__(self, cdb, ibf, db, *, meta=None, bunch=None):
        self.cdb = cdb
        self.ibf = ibf
        self.db = db
        self.meta = meta or {}
        self.bunch = bunch
        self._tiff_handlers = None

    @property
    def tiff_handlers(self):
        if self._tiff_handlers is None:
            self._tiff_handlers = [None] * self.ibf.image_count()
        return self._tiff_handlers

    def tiff_handler(self, form_index):
        th = self.tiff_handlers[form_index]
        if th is None:
            th = TiffHandler(self.ibf, form_index)
            self._tiff_handlers[form_index] = th
        return th

    @classmethod
    def init_from_bunch(cls, databunch, create_persistent_db=False,
                        delay_load=False, access='write', log=None):
        """
        Return a new Batch instance based on the given databunch.
        """
        # If delay_load is True, we can not access the form data via
        # cdb_tool.FormBatch.forms (the list contains only callables then).
        # This complicates the code a lot and I think delaying the loading does
        # not affect the performance that much.
        assert delay_load == False
        # prevent recursive imports
        # ideally classes from cdb_tool should be located below ".storage" as
        # they deal with the on-disk data layout.
        from ddc.tool.cdb_tool import FormBatch
        cdb = FormBatch(databunch.cdb, delay_load=False, access=access, log=log)
        ibf = ImageBatch(databunch.ibf, delay_load=delay_load, access=access, log=log)
        db_path = databunch.db
        if db_path is None:
            is_readonly = (access == 'read')
            if create_persistent_db:
                assert not is_readonly
                if db_path is None:
                    db_path = guess_path(databunch.cdb, type_='db')
            databunch = DataBunch.merge(databunch, db=db_path)
            sqlite_db = SQLiteDB.create_new_db(db_path, create_file=create_persistent_db, log=log)
        elif isinstance(db_path, SQLiteDB):
            sqlite_db = db_path
        else:
            sqlite_db = SQLiteDB.init_with_file(db_path)
        batch = Batch(cdb, ibf, sqlite_db, bunch=simple_bunch(databunch))

        log = l_(log)
        verification_tasks = batch.tasks(type_=TaskType.VERIFICATION, status=TaskStatus.NEW)
        forms_with_errors = []
        for task in verification_tasks:
            msg = 'form #%d: %s' % (task.form_index, task.field_name)
            forms_with_errors.append(msg)
        if forms_with_errors:
            log.debug('remaining verification tasks in ' + ', '.join(forms_with_errors))
        else:
            log.debug('no verification tasks found')
        return batch

    def commit(self):
        self.cdb.commit()
        self.db.commit()

    def close(self):
        self.db.rollback()
        self.db.close()
        self.cdb.close()
        self.ibf.close()

    # --- accessing data ------------------------------------------------------
    def tasks(self, type_=None, status=None, form_index=None):
        Task = self.db.Task
        query_all = self.db.query(Task)

        conditions = []
        attrs = (
            ('form_index', form_index),
            ('type_', type_),
            ('status', status)
        )
        for attr, value in attrs:
            if value is not None:
                conditions.append(getattr(Task, attr) == value)
        if not conditions:
            return query_all.all()
        return query_all.filter(and_(*conditions)).all()

    def new_tasks(self, type_=None, **kwargs):
        return self.tasks(type_=type_, status=TaskStatus.NEW, **kwargs)

    def pic_for_form(self, form_index):
        return self.batch_form(form_index).pic()

    def form(self, i):
        return self.cdb.forms[i]

    def forms(self):
        return self.cdb.forms

    def batch_form(self, form_index):
        return BatchForm(self, form_index)

    def db_form(self, form_index):
        session = self.db.session
        return DBForm(session, form_index, self.db.model)

    def get_setting(self, key, value_only=True):
        session = self.db.session
        BatchData = self.db.model.BatchData
        option = session.query(BatchData).filter(BatchData.key == key).first()
        if not value_only:
            return option
        return option.value if (option is not None) else None

    def store_setting(self, key, value=DELETE):
        BatchData = self.db.model.BatchData
        if value is DELETE:
            setting_ = self.get_setting(key, value_only=False)
            if setting_:
                self.db.session.delete(setting_)
            return None
        setting = get_or_add(BatchData, self.db.session, {'key': key})
        setting.value = value
