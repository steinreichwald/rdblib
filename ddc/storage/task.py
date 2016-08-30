# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from datetime import datetime

from durus.persistent import PersistentObject as Persistent

from ddc.lib.attribute_dict import AttrDict


__all__ = ['Task', 'TaskStatus', 'TaskType']

class TaskStatus(object):
    NEW = 'new'
    IN_PROGRESS = 'in_progress'
    CLOSED = 'closed'


class TaskType(object):
    VERIFICATION = 'manual_verification'
    FORM_VALIDATION = 'form_validation'


class Task(Persistent):
    def __init__(self, form_position, type_, status=TaskStatus.NEW, data=None, created=None, last_modified=None):
        self.form_position = form_position
        self.type_ = type_
        self.status = status
        if data is None:
            data = AttrDict()
        self.data = data

        self.created = created or datetime.now()
        self.last_modified = last_modified or datetime.now()

    def copy(self):
        return Task(
            self.form_position,
            self.type_,
            status=self.status,
            data=self.data.copy(),
            created=self.created,
            last_modified=self.last_modified,
        )

    def close(self):
        self.status = TaskStatus.CLOSED
        self.last_modified = datetime.now()

    def __eq__(self, other):
        attrs = ('form_position', 'type_', 'status', 'data', 'created', 'last_modified')
        for name in attrs:
            if not hasattr(other, name):
                return False
            elif getattr(self, name) != getattr(other, name):
                return False
        return True

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return 'Task<form_position=%r, type_=%r, status=%r: %r>' % (self.form_position, self.type_, self.status, self.data)

