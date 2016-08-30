# -*- coding: utf-8 -*-
"""
The basic idea is that we always need a triple to access all relevant information.
  1. CDB files for extracted text data
  2. IBF for actual images (scans)
  3. Durus DB for meta data

DataBunch represents the path information for that triple (so no file system
access or active databases required). The Batch is the main abstraction which
hides all implementation details (as much as possible/sensible).
"""

from __future__ import division, absolute_import, print_function, unicode_literals

from ddc.lib.dict_merger import merge_dicts
from ddc.lib.log_proxy import l_
from .durus_ import DurusDB, DurusKey
from .paths import guess_path
from .task import TaskStatus, TaskType


__all__ = ['Batch']

class Batch(object):
    def __init__(self, cdb, ibf, durus_db, meta=None):
        self.cdb = cdb
        self.ibf = ibf
        self.durus_db = durus_db
        self.meta = meta or {}
        self._tiff_handler = None

    @classmethod
    def init_from_bunch(cls, databunch, create_new_durus=False,
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
        durus_path = databunch.durus
        if create_new_durus:
            if durus_path is None:
                durus_path = guess_path(databunch.cdb, type_='durus')
            durus_db = DurusDB.create_new_db(durus_path, log=log)
            cls._create_snapshot(cdb, durus_db)
        elif isinstance(durus_path, DurusDB):
            durus_db = durus_path
        else:
            readonly = (access == 'read')
            durus_db = DurusDB.init_with_file(durus_path, readonly=readonly)
            # LATER: verify snapshot and record change if necessary
        batch = Batch(cdb, ibf, durus_db)

        log = l_(log)
        verification_tasks = batch.tasks(type_=TaskType.VERIFICATION, status=TaskStatus.NEW)
        forms_with_errors = []
        for task in verification_tasks:
            msg = 'form #%d: %s' % (task.form_position, task.data['field_name'])
            forms_with_errors.append(msg)
        if forms_with_errors:
            log.debug('remaining verification tasks in ' + ', '.join(forms_with_errors))
        else:
            log.debug('no verification tasks found')
        return batch

    def commit(self):
        self.durus_db.commit()

    def close(self):
        self.durus_db.rollback()
        self.durus_db.close()
        self.cdb.close()
        self.ibf.close()

    # --- data integrity ------------------------------------------------------
    @classmethod
    def _create_snapshot(cls, cdb, durus_db):
        durus_db.insert_snapshot('cdb', [cdb.filecontent[:]])

    # --- accessing data ------------------------------------------------------
    @property
    def durus(self):
        """Returns the <root> of the Durus database.
        Hint: If you need access to this property you please think about adding
        a method to this class."""
        return self.durus_db.root

    def tasks(self, type_=None, status=None, form_position=None):
        all_tasks = self.durus[DurusKey.TASKS]
        if (type_ is None) and (status is None) and (form_position is None):
            return all_tasks

        def _matches(task, attr_name, attr_value):
            if attr_value is None:
                return True
            return (getattr(task, attr_name) == attr_value)
        matching_tasks = []
        for task in all_tasks:
            if (_matches(task, 'type_', type_) and _matches(task, 'status', status)
                    and _matches(task, 'form_position', form_position)):
                matching_tasks.append(task)
        return matching_tasks

    def new_tasks(self, type_=None, **kwargs):
        params = merge_dicts({'status': TaskStatus.NEW, 'type_': type_}, kwargs)
        return self.tasks(**params)

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

    def ignored_warnings(self, form_index):
        if DurusKey.IGNORED_WARNINGS not in self.durus:
            self.durus_db._create_initial_structure()

        ignores = []
        for ignore_item in self.durus[DurusKey.IGNORED_WARNINGS]:
            ignore_form_index = ignore_item[0]
            ignore_key = ignore_item[1:]
            if form_index == ignore_form_index:
                ignores.append(ignore_key)
        return tuple(ignores)

    def store_ignored_warning(self, form_index, field_name, error_key, field_value):
        ignore_key = (field_name, error_key, field_value)
        db_item = (form_index, ) + ignore_key
        if db_item not in self.durus[DurusKey.IGNORED_WARNINGS]:
            self.durus[DurusKey.IGNORED_WARNINGS].append(db_item)
