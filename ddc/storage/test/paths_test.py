# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

import os

from ddt import ddt as DataDrivenTestCase, data
from pythonic_testcase import *

from ddc.storage.paths import *


def fix_path(path):
    os_path = path.replace('/', os.path.sep)
    if os_path.startswith('\\'):
        # Windows: add drive letter for absolute paths without drive letter
        # qualification
        os_path = os.path.abspath(os_path)
    return os_path
# short-hand alias to keep the code as readable as possible
f = fix_path

@DataDrivenTestCase
class PathTest(PythonicTestCase):
    def test_path_info_from_cdb(self):
        # using os.path.join here so we can test also Windows-style paths if
        # running the tests on Windows
        cdb_dir = os.path.join('tmp', 'foo', 'bar')
        cdb_path = os.path.join(cdb_dir, 'abc.cdb')
        assert_equals((cdb_dir, 'abc'), path_info_from_cdb(cdb_path))

    def test_path_info_from_ibf(self):
        ibf_dir = os.path.join('tmp', 'foo', 'bar')
        ibf_path = os.path.join(ibf_dir, '00000001', 'abc.ibf')
        assert_equals((ibf_dir, 'abc'), path_info_from_ibf(ibf_path))
        with assert_raises(ValueError):
            path_info_from_ibf(os.path.join(ibf_dir, 'abc.ibf'))

    def test_path_info_from_db(self):
        db_dir = os.path.join('tmp', 'foo', 'bar')
        db_path = os.path.join(db_dir, 'abc.db')
        assert_equals((db_dir, 'abc'), path_info_from_db(db_path))

    def test_guess_cdb_path(self):
        cdb_dir = os.path.join('tmp', 'foo', 'bar')
        cdb_path = os.path.join(cdb_dir, 'abc.CDB')
        assert_equals(cdb_path, guess_cdb_path(cdb_dir, 'abc'))

    def test_guess_ibf_path(self):
        ibf_dir = os.path.join('tmp', 'foo', 'bar')
        ibf_path = os.path.join(ibf_dir, '00000001', 'abc.IBF')
        assert_equals(ibf_path, guess_ibf_path(ibf_dir, 'abc'))

    def test_guess_db_path(self):
        db_dir = os.path.join('tmp', 'foo', 'bar')
        db_path = os.path.join(db_dir, 'abc.db')
        assert_equals(db_path, guess_db_path(db_dir, 'abc'))

    def test_cdb_path_calculation_is_reversible(self):
        path_info = ('foo', 'bar.cdb')
        assert_equals(
            path_info,
            path_info_from_cdb(guess_cdb_path(*path_info))
        )

    def test_ibf_path_calculation_is_reversible(self):
        path_info = ('foo', 'bar.ibf')
        assert_equals(
            path_info,
            path_info_from_ibf(guess_ibf_path(*path_info))
        )

    def test_db_path_calculation_is_reversible(self):
        path_info = ('foo', 'bar.db')
        assert_equals(
            path_info,
            path_info_from_db(guess_db_path(*path_info))
        )

    @data('cdb', 'ibf', 'db', 'ask')
    def test_can_guess_bunch_from_path(self, missing):
        bunch = DataBunch(cdb=f('/tmp/foo.CDB'), ibf=f('/tmp/00000001/FOO.ibf'),
                          db=f('/tmp/Foo.db'), ask=f('/tmp/00000001/FOO.ask'))
        noise = f('/foo.' + missing)
        fn_map = {noise: noise}
        for key in bunch:
            if key != missing:
                fn_map[key.lower()] = key
        source_attr = getattr(bunch, missing)
        guessed_bunch = guess_bunch_from_path(source_attr, fn_map)
        assert_equals(bunch, guessed_bunch)

    def test_guess_bunch_from_path_normalizes_input_path_before_lookup(self):
        # the input path might not be normalized but that should not confuse
        # the guessing.
        input_path = '/tmp/../tmp/foo.CDB'
        fn_map = {
            f('/tmp/foo.cdb'): f('/tmp/FOO.CDB'),
            f('/tmp/00000001/foo.ibf'): f('/tmp/00000001/foo.IBF'),
        }
        bunch = DataBunch(
            cdb=f('/tmp/foo.CDB'), ibf=f('/tmp/00000001/foo.IBF'),
            db=None, ask=None
        )
        guessed_bunch = guess_bunch_from_path(input_path, fn_map)
        assert_equals(bunch, guessed_bunch)

    def test_guess_bunch_uses_absolute_paths_in_lookup(self):
        cwd = os.getcwd()
        input_path = './foo.CDB'
        cdb_path = f(os.path.join(cwd, 'foo.CDB'))
        cdb_key = f(cdb_path.lower())
        ibf_path = f(os.path.join(cwd, ibf_subdir, 'foo.IBF'))
        ibf_key = f(ibf_path.lower())
        fn_map = {
            cdb_key: cdb_path,
            ibf_key: ibf_path,
        }
        bunch = DataBunch(cdb=cdb_path, ibf=ibf_path, db=None, ask=None)
        guessed_bunch = guess_bunch_from_path(input_path, fn_map)
        assert_equals(bunch, guessed_bunch)

    def test_guess_path(self):
        assert_equals(f('/tmp/00000001/foo.IBF'), guess_path(f('/tmp/foo.CDB'), type_='ibf'))
        assert_equals(f('/tmp/foo.db'), guess_path(f('/tmp/foo.CDB'), type_='db'))
        assert_equals(f('/tmp/00000001/foo.ask'), guess_path(f('/tmp/foo.db'), type_='ask'))
        assert_equals(
            f('/tmp/00000001/foo.IBF'),
            guess_path(f('/tmp/foo.RDB'), type_='ibf'),
            message='can guess paths based on RDB filenames'
        )
        assert_equals(f('/tmp/00000001/foo.ASC'), guess_path(f('/tmp/foo.db'), type_='asc'))
        assert_equals(
            f('/tmp/00000001/foo.IBF'),
            guess_path(f('/tmp/foo.CDB'), type_='IBF'),
            message='ignores "type_" casing')

