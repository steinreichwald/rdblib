# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from babel.util import LOCALTZ
from datetime import datetime as DateTime_

from sqlalchemy import Column, Integer, String, UnicodeText
from sqlalchemy.ext.declarative import declarative_base

from ddc.lib.attribute_dict import AttrDict
from ddc.lib.jsontype_column import JSONType
from ddc.lib.utc_datetime_column import UTCDateTime
from ddc.storage.task import TaskStatus


__all__ = ['get_model', 'LATEST']

LATEST = 'v201609'

def get_model(revision=LATEST):
    """
    Return the model classes for the given revision.

    We may need to change the database layout in incompatible ways for future
    versions of pydica. However I don't want to upgrade old databases. This
    level of indirection actually helps us to represent different DB layouts
    (of course also other parts of pydica must be able to deal with the
    differences but this is the first step).
    """
    revisions = {
        'v201609': v201609,
    }
    if revision not in revisions:
        revision_list = ', '.join(revisions)
        raise ValueError('Unknown revision %r -- should be one of %s' % (revision, revision_list))
    return revisions[revision]()

# -----------------------------------------------------------------------------
# We need a way to identify the DB schema for arbitrary databases in a reliable
# way so we assume that the DB version table is always present. Therefore the
# model is configured at a module level.
VersionBase = declarative_base()
class DBVersion(VersionBase):
    __tablename__ = 'dbversion'
    version_id = Column(String, primary_key=True)
    data = Column(String, nullable=True)

# -----------------------------------------------------------------------------
def v201609():
    Base = declarative_base()
    metadata = Base.metadata

    class IgnoredWarning(Base):
        __tablename__ = 'ignored_warnings'
        id = Column(Integer, primary_key=True)
        form_index = Column(Integer, nullable=False)
        field_name = Column(String, nullable=False)
        error_key = Column(String, nullable=False)
        field_value = Column(UnicodeText)
        # data is not used right now but should provide some flexibility to
        # add additional data without upgrading the DB schema.
        data = Column(JSONType, nullable=False, default=dict)


    class Task(Base):
        __tablename__ = 'tasks'
        id = Column(Integer, primary_key=True)
        form_index = Column(Integer, nullable=False)
        type_ = Column(String, nullable=False)
        field_name = Column(String, nullable=True)
        status = Column(String, nullable=False)
        data = Column(JSONType, nullable=False, default=dict)
        created = Column(UTCDateTime, nullable=False, default=lambda: DateTime_.now(tz=LOCALTZ))
        last_modified = Column(UTCDateTime, nullable=False, default=lambda: DateTime_.now(tz=LOCALTZ))

        def __init__(self, form_index, type_, *, field_name=None, status=TaskStatus.NEW, data=None):
            self.form_index = form_index
            self.type_ = type_
            self.field_name = field_name
            self.status = status
            self.data = data if (data is not None) else {}

        def close(self):
            self.status = TaskStatus.CLOSED
            self.last_modified = DateTime_.now(tz=LOCALTZ)

        def __repr__(self):
            tmpl = '%s<id=%r, form_index=%r, type_=%r, status=%r, ... [%r]>'
            klass = self.__class__.__name__
            params = (klass, self.id, self.form_index, self.type_, self.status, id(self))
            return tmpl % params


    class BatchData(Base):
        __tablename__ = 'batch_data'
        key = Column(String, primary_key=True)
        value = Column(UnicodeText, nullable=False, default=u'')

    class FormData(Base):
        __tablename__ = 'form_data'
        form_index = Column(Integer, primary_key=True, autoincrement=False)
        key = Column(String, primary_key=True)
        value = Column(UnicodeText, nullable=False, default=u'')

    return AttrDict(
        id='v201609',
        metadata=metadata,

        BatchData=BatchData,
        FormData=FormData,
        IgnoredWarning=IgnoredWarning,
        Task=Task,
    )


