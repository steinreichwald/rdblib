# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import os
from ddc.platf.platform_quirks import is_windows

if is_windows():
    import win32con, win32file, pywintypes # http://sf.net/projects/pywin32/
else:
    import fcntl


__all__ = ['acquire_lock', 'unlock']

# -----------------------------------------------------------------------------
# initial locking code copied from Durus (durus/file.py) but with custom
# modifications
def acquire_lock(file_, exclusive_lock=True, raise_on_error=True, log=None):
    """Lock the given file-like object to prevent other processes from
    accessing is.

    Parameters
      exclusive_lock [default: True]
          acquire an exclusive lock so no other process can read or write from
          the file (if False: only prevent others from writing to the file)
      raise_on_error [default: True]
          if True, raise an exception if the file can not be locked (return a
          boolean indicating success/failure otherwise)
      log [default None]
          logger instance used for optional log messages (if None nothing will
          be logging)
    """
    if log:
        lock_msg = '[%d] locking %r' % (os.getpid(), file_.name)
        log.debug(lock_msg)
    if is_windows():
        fd = win32file._get_osfhandle(file_.fileno())
        if exclusive_lock:
            lock_flags = (win32con.LOCKFILE_EXCLUSIVE_LOCK | win32con.LOCKFILE_FAIL_IMMEDIATELY)
        else:
            lock_flags = win32con.LOCKFILE_FAIL_IMMEDIATELY
        try:
            win32file.LockFileEx(fd, lock_flags, 0, -65536, pywintypes.OVERLAPPED())
        except pywintypes.error as e:
            if log:
                log.warn('[%d] error while trying to lock %r: %r' % (os.getpid(), file_.name, e))
            if raise_on_error:
                raise OSError(e)
            return False
    else:
        if exclusive_lock:
            lock_flags = (fcntl.LOCK_EX | fcntl.LOCK_NB)
        else:
            lock_flags = (fcntl.LOCK_SH | fcntl.LOCK_NB)
        try:
            fcntl.flock(file_, lock_flags)
        except (BlockingIOError, PermissionError) as e:
            if log:
                log.warn('[%d] error while trying to lock %r: %r' % (os.getpid(), file_.name, e))
            if raise_on_error:
                raise
            return False
    return True

def unlock(file_, log=None):
    if log:
        lock_msg = '[%d] unlocking %r' % (os.getpid(), file_.name)
        log.debug(lock_msg)
    if is_windows():
        fd = win32file._get_osfhandle(file_.fileno())
        win32file.UnlockFileEx(fd, 0, -65536, pywintypes.OVERLAPPED())
    else:
        fcntl.flock(file_, fcntl.LOCK_UN)
# -----------------------------------------------------------------------------

