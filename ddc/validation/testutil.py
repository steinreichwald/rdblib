# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from contextlib import contextmanager
import shutil
from tempfile import mkdtemp


__all__ = ['use_tempdir']

@contextmanager
def use_tempdir():
    tempdir_path = mkdtemp()
    yield tempdir_path
    shutil.rmtree(tempdir_path)

