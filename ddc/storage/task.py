# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals


__all__ = ['TaskStatus', 'TaskType']

class TaskStatus(object):
    NEW = 'new'
    IN_PROGRESS = 'in_progress'
    CLOSED = 'closed'


class TaskType(object):
    VERIFICATION = 'manual_verification'
    FORM_VALIDATION = 'form_validation'

