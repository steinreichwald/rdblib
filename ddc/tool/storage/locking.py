# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import os


def is_windows():
    return (os.name == 'nt')

if is_windows():
    import win32con, win32file, pywintypes # http://sf.net/projects/pywin32/
else:
    import fcntl


__all__ = ['is_windows', 'acquire_lock', 'unlock']

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
                raise IOError("Unable to obtain lock")
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

def _is_locked(file_or_filename, exclusive_lock=True):
    """Returns True if the file-like object is locked BY ANOTHER PROCESS!

    Attention: Do NOT call this method directly if your process already has
    a lock for the file as the code will remove the lock afterwards!.
    """
    # It seems as if the only way to actually test the locking state of a
    # file descriptor is to actually open it and try to acquire the lock.
    # At least I was unable to find any API which could be used to retrieve that
    # information without actually trying to lock the file (fs/Jan 2015).
    # Even worse: After lock acquisition we don't know if we acquired a new
    # lock or if we held the lock before. Therefore we have to unlock the
    # file after a successful test.
    if isinstance(file_or_filename, str):
        try:
            file_ = open(file_or_filename)
        except PermissionError:
            if is_windows():
                # on Windows opening a file means we can not open it a second
                # time (open will raise a PermissionError instead) so treat the
                # file as locked.
                return True
            raise
    acquired_lock = acquire_lock(file_, exclusive_lock=exclusive_lock, raise_on_error=False)
    if acquired_lock:
        unlock(file_)
        return False
    return True
