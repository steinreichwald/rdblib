################################################################################
### name(less|d)tuple
################################################################################

'''
This is a replacement for collections.namedtuple (python 3.3).
It has the same semantics, but makes pickling as easy for
the user as tuples.

This is only true for the generated classes.
Subclasses need to do their own pickling, again.
'''

from keyword import iskeyword as _iskeyword
from operator import itemgetter as _itemgetter

from six import exec_


_refmodule = 'ddc.tool.tupletool'

_class_template = '''\
from builtins import property as _property, tuple as _tuple
from operator import itemgetter as _itemgetter
from collections import OrderedDict
from {refmodule} import _rebuild_namelesstuple, _rebuild_namedtuple

class {typename}(tuple):
    '{typename}({arg_list})'

    __slots__ = ()

    _fields = {field_names!r}

    def __new__(_cls, {arg_list}):
        'Create new instance of {typename}({arg_list})'
        return _tuple.__new__(_cls, ({arg_list}))

    @classmethod
    def _make(cls, iterable, new=tuple.__new__, len=len):
        'Make a new {typename} object from a sequence or iterable'
        result = new(cls, iterable)
        if len(result) != {num_fields:d}:
            raise TypeError('Expected {num_fields:d} arguments, got %d' % len(result))
        return result

    def __repr__(self):
        'Return a nicely formatted representation string'
        name = self.__class__.__name__
        if name == '_':
            name = ''
        return name + '({repr_fmt})' % self

    def _asdict(self):
        'Return a new OrderedDict which maps field names to their values'
        return OrderedDict(zip(self._fields, self))

    __dict__ = property(_asdict)

    def _replace(_self, **kwds):
        'Return a new {typename} object replacing specified fields with new values'
        result = _self._make(map(kwds.pop, {field_names!r}, _self))
        if kwds:
            raise ValueError('Got unexpected field names: %r' % list(kwds))
        return result

    def __getnewargs__(self):
        'Return self as a plain tuple.  Used by copy and pickle.'
        # will be called if we fall back to the inherited __reduce_ex__
        return tuple(self)

{field_defs}
'''

_repr_template = '{name}=%r'

_field_template = '''\
    {name} = _property(_itemgetter({index:d}), doc='Alias for field number {index:d}')
'''

def namelesstuple(field_names, verbose=False, rename=False, typename='_'):
    """Returns a new subclass of tuple with named fields.

    >>> point = namelesstuple(['x', 'y'])
    >>> point.__doc__                   # docstring for the new class
    '(x, y)'
    >>> p = point(11, y=22)             # instantiate with positional args or keywords
    >>> p[0] + p[1]                     # indexable like a plain tuple
    33
    >>> x, y = p                        # unpack like a regular tuple
    >>> x, y
    (11, 22)
    >>> p.x + p.y                       # fields also accessable by name
    33
    >>> d = p._asdict()                 # convert to a dictionary
    >>> d['x']
    11
    >>> point(**d)                      # convert from a dictionary
    (x=11, y=22)
    >>> p._replace(x=100)               # _replace() is like str.replace() but targets named fields
    (x=100, y=22)

    """
    if isinstance(field_names, tuple):
        if typename == '_':
            res = classcache.get(field_names)
        else:
            res = classcache.get((typename, field_names))
        if res:
            return res

    # Validate the field names.  At the user's option, either generate an error
    # message or automatically replace the field name with a valid name.
    if isinstance(field_names, str):
        field_names = field_names.replace(',', ' ').split()
    field_names = list(map(str, field_names))
    if rename:
        seen = set()
        for index, name in enumerate(field_names):
            if (not all(c.isalnum() or c=='_' for c in name)
                or _iskeyword(name)
                or not name
                or name[0].isdigit()
                or name.startswith('_')
                or name in seen):
                field_names[index] = '_%d' % index
            seen.add(name)
    for name in [typename] + field_names:
        if not all(c.isalnum() or c=='_' for c in name):
            raise ValueError('Type names and field names can only contain '
                             'alphanumeric characters and underscores: %r' % name)
        if _iskeyword(name):
            raise ValueError('Type names and field names cannot be a '
                             'keyword: %r' % name)
        if name[0].isdigit():
            raise ValueError('Type names and field names cannot start with '
                             'a number: %r' % name)
    seen = set()
    for name in field_names:
        if name.startswith('_') and not rename:
            raise ValueError('Field names cannot start with an underscore: '
                             '%r' % name)
        if name in seen:
            raise ValueError('Encountered duplicate field name: %r' % name)
        seen.add(name)

    # Fill-in the class template

    # note that unique ensures minimal classes
    field_names = unique[tuple(field_names)]
    class_definition = _class_template.format(
        typename = typename,
        field_names = field_names,
        num_fields = len(field_names),
        arg_list = repr(tuple(field_names)).replace("'", "")[1:-1],
        repr_fmt = ', '.join(_repr_template.format(name=name)
                             for name in field_names),
        field_defs = '\n'.join(_field_template.format(index=index, name=name)
                               for index, name in enumerate(field_names)),
        refmodule = _refmodule,
    )

    # Execute the template string in a temporary namespace and support
    # tracing utilities by setting a value for frame.f_globals['__name__']
    if typename == '_':
        namespace = dict(__name__='namelesstuple_%s' % ('_'.join(field_names)))
    else:
        namespace = dict(__name__='namedtuple_%s' % typename)
    try:
        exec_(class_definition, namespace)
    except SyntaxError as e:
        raise SyntaxError(e.msg + ':\n\n' + class_definition)
    result = namespace[typename]
    result._source = class_definition
    if verbose:
        print(result._source)
    # capture the class in the cache
    if typename == '_':
        classcache[field_names] = result
    else:
        classcache[(typename, field_names)] = result
    copyreg.pickle(result, reduction_function)
    return result


def namedtuple(typename, field_names, verbose=False, rename=False):
    return namelesstuple(field_names, verbose, rename, typename)


class _UniqeDict(dict):
    '''
    A dict that stores its records and returns a unique version of that key'
    Usage: str_val = unique[str_val]
    '''
    def __missing__(self, key):
        self[key] = key
        return key

unique = _UniqeDict()

classcache = {}

def _rebuild_namelesstuple(args, fields):
    try:
        klass = classcache[fields]
    except KeyError:
        klass = namelesstuple(fields)
    return klass._make(args)

def _rebuild_namedtuple(args, name, fields):
    try:
        klass = classcache[(name, fields)]
    except KeyError:
        klass = namedtuple(name, fields)
    return klass._make(args)


import copyreg

def reduction_function(self):
    'Return self as a plain tuple plus definition. Used by copy and pickle.'
    if self.__class__.__name__ == '_':
        return (_rebuild_namelesstuple, (tuple(self), self._fields))
    else:
        return (_rebuild_namedtuple, (tuple(self), self.__class__.__name__,
                                       self._fields))
