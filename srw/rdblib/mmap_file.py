# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import io
import mmap
import os
import sys
from timeit import default_timer as timer

from .lib.log_proxy import l_
from .locking import acquire_lock


__all__ = ['MMapFile']

FORCE_LOAD = False  # set to True to effectively disable mmap

class MMapFile(mmap.mmap):
    """
    memory-like file, based on mmap.
    The file does intentionally not support the standard file interface but
    only the methods that make sense for our purpose.
    """

    #----------------------------------------------------------------------
    def __new__(cls, filename, access, log=None):
        """
        Simplified constructor
        ----------------------

        MMapFile supports array-like access, only. All file-like methods
        are removed.

        access is "read", "write", or "copy".
        (As a short-term workaround we also have "dontcare" which works like
         "write" but does not do any locking.)

        "copy" means copy_on_write: Data is written to memory, only.

        """
        access = access.upper()
        if access != 'DONTCARE':
            access_mode = getattr(mmap, 'ACCESS_' + access)
        else:
            access_mode = mmap.ACCESS_WRITE
        if access_mode == mmap.ACCESS_READ:
            aflags = 'rb'
        else:
            aflags = 'r+b'
        log = l_(log)

        start = timer()

        # Locking requires file descriptors/handles. mmap.mmap creates an
        # internal file descriptor which we can not access. Therefore we have
        # to save a reference to the underlying file ourself.
        f = io.open(filename, aflags)
        if access != 'DONTCARE':
            try:
                acquire_lock(f, exclusive_lock=(access_mode == mmap.ACCESS_WRITE), log=log)
            except:
                # On Windows we can not move/rename open files so leaving the
                # file open would mean we might trigger other exceptions later
                # on.
                f.close()
                raise
        self = super(MMapFile, cls).__new__(cls, f.fileno(), 0, access=access_mode)
        self._file = f
        self._name = filename
        self._closed = False
        self._access = access_mode

        duration = timer() - start
        log.debug('opened file %s in %.5f seconds', filename, duration)

        if FORCE_LOAD:
            start = timer()
            # just to check the effect of mmap
            self[:]
            duration = timer() - start
            basename = os.path.basename(filename)
            log.debug('force loading of %s tool %.5f seconds', basename, duration)
        return self

    if sys.platform == 'win32':
        # windows will return 0 if an error occurred. Linux/Mac raise an error.
        # this description is misleading. It is actually the behavior of
        # FlushViewOfFile that returns 0 on error.
        # But the behavior on access_read or access_copy is explicitly
        # inserted by Python's C implementation.
        # I think this behavior is not very useful, and we should treat this
        # as a successful no-op.
        def flush(self, *args, **kw):
            ret = super(MMapFile, self).flush(*args, **kw)
            if (ret == 0) and (self._access == mmap.ACCESS_WRITE):
                # this is a real error.
                # ACCESS_READ or ACCESS_COPY return 0 as a no-op.
                raise WindowsError('something went wrong in flush().')
            return ret

    def close(self):
        super(MMapFile, self).close()
        # Closing the file will also release the lock implicitely...
        if not self._file.closed:
            self._file.close()
        self._closed = True

    @property
    def closed(self):
        return self._closed

    @property
    def name(self):
        return self._name

    def __getattribute__(self, name):
        if name in ('flush', 'close', 'closed', 'name') or name.startswith('_'):
            return super(MMapFile, self).__getattribute__(name)
        raise AttributeError("type object '{}' has no attribute '{}'"
                             .format(self.__class__.__name__, name))
