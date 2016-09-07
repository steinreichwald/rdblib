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
from .paths import guess_path
from .sqlite import get_or_add, DBForm, SQLiteDB
from .task import TaskStatus, TaskType
from .utils import DELETE


__all__ = ['Batch']

class Batch(object):
    def __init__(self, cdb, ibf, db, meta=None):
        self.cdb = cdb
        self.ibf = ibf
        self.db = db
        self.meta = meta or {}
        self._tiff_handler = None

    @classmethod
    def init_from_bunch(cls, databunch, create_new_db=False,
                        delay_load=False, access='write', log=None):
        """
        Return a new Batch instance based on the given databunch.
        """
        # prevent recursive imports
        # ideally classes from cdb_tool should be located below ".storage" as
        # they deal with the on-disk data layout.
        from ddc.tool.cdb_tool import ImageBatch, FormBatch
        cdb = FormBatch(databunch.cdb, delay_load=delay_load, access=access, log=log)
        ibf = ImageBatch(databunch.ibf, delay_load=delay_load, access=access, log=log)
        db_path = databunch.db
        if create_new_db:
            if db_path is None:
                db_path = guess_path(databunch.cdb, type_='db')
            sqlite_db = SQLiteDB.create_new_db(db_path, log=log)
        elif isinstance(db_path, SQLiteDB):
            sqlite_db = db_path
        else:
            readonly = (access == 'read')
            sqlite_db = SQLiteDB.init_with_file(db_path, create=False, log=log)
        batch = Batch(cdb, ibf, sqlite_db)

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
        image_data = self.ibf.image_entries[form_index]
        ibf_rec_pic = image_data.rec.codnr
        if ibf_rec_pic != 'DELETED':
            return ibf_rec_pic

        if (self._tiff_handler is None):
            self._tiff_handler = [None] * self.ibf.image_count()
        th = self._tiff_handler[form_index]
        if th is None:
            from ddc.tool.cdb_tool import TiffHandler
            th = TiffHandler(self.ibf, form_index)
            self._tiff_handler[form_index] = th
        ibf_long_pic = th.long_data2.rec.page_name
        return ibf_long_pic

    def form(self, i):
        return self.cdb.forms[i]

    def forms(self):
        return self.cdb.forms

    def db_form(self, form_index):
        session = self.db.session
        return DBForm(session, form_index, self.db.model)

    def get_setting(self, key):
        session = self.db.session
        BatchData = self.db.model.BatchData
        option = session.query(BatchData).filter(BatchData.key == key).first()
        if option is None:
            return None
        return option.value

    def store_setting(self, key, value=DELETE):
        BatchData = self.db.model.BatchData
        session = self.db.session
        if value is DELETE:
            setting_ = session.query(BatchData).filter(BatchData.key == key).first()
            if setting_:
                setting_.delete()
            return None
        return get_or_add(BatchData, session, {'key': key}, {'value': value})
