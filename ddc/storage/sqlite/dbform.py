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

from ddc.lib.dict_merger import merge_dicts
from ..task import TaskStatus
from ..utils import DELETE


__all__ = ['get_or_add', 'DBForm']

def get_or_add(orm_class, session, primary_keys, other_values=None):
    conditions = []
    for key, value in primary_keys.items():
        column = getattr(orm_class, key)
        conditions.append(column == value)
    db_item = session.query(orm_class).filter(and_(*conditions)).first()
    if db_item is None:
        db_item = orm_class(**primary_keys)
        for key, value in (other_values or {}).items():
            assert hasattr(db_item, key)
            setattr(db_item, key, value)
    session.add(db_item)
    return db_item


class DBForm(object):
    def __init__(self, session, form_index, model):
        self.session = session
        self.form_index = form_index
        self.model = model

    def query_tasks(self):
        Task = self.model.Task
        return self.session.query(Task).filter(Task.form_index == self.form_index)

    def tasks(self, **kw_conditions):
        Task = self.model.Task
        conditions = []
        for attr_name, filter_value in kw_conditions.items():
            c = (getattr(Task, attr_name) == filter_value)
            conditions.append(c)
        if not conditions:
            return tuple(self.query_tasks())
        return tuple(self.query_tasks().filter(and_(*conditions)))

    def new_tasks(self, type_=None, **kwargs):
        params = merge_dicts({'status': TaskStatus.NEW, 'type_': type_}, kwargs)
        return self.tasks(**params)

    def add_task(self, **kwargs):
        Task = self.model.Task
        task = Task(form_index=self.form_index, **kwargs)
        self.session.add(task)
        return task

    def query_ignored_warnings(self):
        IgnoredWarning = self.model.IgnoredWarning
        return self.session.query(IgnoredWarning).filter(IgnoredWarning.form_index == self.form_index)

    def ignored_warnings(self, as_ignore_key=False):
        warnings_ = tuple(self.query_ignored_warnings())
        if not as_ignore_key:
            return warnings_
        to_ignore_key = lambda i: (i.field_name, i.error_key, i.field_value)
        return tuple(map(to_ignore_key, warnings_))

    def add_ignored_warning(self, field_name, error_key, field_value):
        IgnoredWarning = self.model.IgnoredWarning
        key_attrs = dict(
            form_index=self.form_index,
            field_name=field_name,
            error_key=error_key,
            field_value=field_value
        )
        return get_or_add(IgnoredWarning, self.session, key_attrs)

    def get_setting(self, key):
        session = self.db.session
        FormData = self.db.model.FormData
        option = session.query(FormData).filter(FormData.key == key).first()
        if option is None:
            return None
        return option.value

    def store_setting(self, key, value=DELETE):
        FormData = self.db.model.FormData
        session = self.db.session
        if value is DELETE:
            setting_ = session.query(FormData).filter(FormData.key == key).first()
            if setting_:
                setting_.delete()
            return None
        return get_or_add(FormData, session, {'key': key}, {'value': value})

