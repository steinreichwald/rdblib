# encoding: utf-8
#
# v1.1 / 2016-09-01 (fs)
#   - MutableDict should inherit from AttrDict

from .attribute_dict import AttrDict


__all__ = ['JSONType']

# ---- copied straight from the SQLAlchemy 0.8.1 manual -----------------------
# ORM Extensions > Mutation Tracking > Establishing Mutability on Scalar Column Values
#   v1.1/fs: inherit from AttrDict

import json
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.types import Text, TypeDecorator

class JSONEncodedDict(TypeDecorator):
    "Represents an immutable structure as a json-encoded string."

    impl = Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class MutableDict(Mutable, AttrDict):
    @classmethod
    def coerce(cls, key, value):
        "Convert plain dictionaries to MutableDict."
        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)
            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        "Detect dictionary set events and emit change events."
        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        "Detect dictionary del events and emit change events."
        dict.__delitem__(self, key)
        self.changed()

JSONType = MutableDict.as_mutable(JSONEncodedDict)
# -----------------------------------------------------------------------------
