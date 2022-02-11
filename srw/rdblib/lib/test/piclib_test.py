
from datetime import date as Date

import freezegun
from pythonic_testcase import *

from ..piclib import (extend_short_pic_str, pic_matches, shorten_long_pic_str,
    PIC)
from ..yearmonth import YearMonth


class PICTest(PythonicTestCase):
    def test_can_instantiate_with_yearmonth(self):
        ym = YearMonth(2021, 2)
        pic = PIC(ym, customer_id_short=123, counter=4)
        assert_equals('10212300004024', pic.to_str())

    def test_str(self):
        pic = PIC(year=2020, month=12, customer_id_short=123, counter=4)
        assert_equals('01212300004024', pic.to_str())
        assert_equals('01212300004024', str(pic))
        assert_equals('012123000040000024', pic.to_str(long_ik=True))

        ym = pic.guess_year_month()
        ym_pic = PIC(ym, pic.customer_id_short, pic.counter)
        assert_equals('01212300004024', str(ym_pic))

    def test_from_str(self):
        pic = PIC(year=2020, month=12, customer_id_short=123, counter=4)
        pic_str = str(pic)
        # only last digit of year is encoded in PIC string
        expected_pic = pic._replace(year=0)
        assert_equals(expected_pic, PIC.from_str(pic_str))

    def test_from_str_long_ik(self):
        pic = PIC(year=2021, month=8, customer_id_short=123, counter=4)
        pic_str = pic.to_str(long_ik=True)
        assert_length(18, pic_str)
        assert_equals(pic, PIC.from_str(pic_str))

    def test_can_increment_counter(self):
        pic = PIC(year=2020, month=12, customer_id_short=123, counter=4)
        new_pic = pic + 1
        assert_equals(pic._replace(counter=5), new_pic)

    def test_can_guess_year(self):
        def _p(year, month=4):
            pic = PIC(year=year, month=month, customer_id_short=123, counter=4)
            return pic.guess_year_month()

        assert_equals(YearMonth(2008, 4), _p(year=2008),
            message='should not guess if complete year is known')

        for y_d in (2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020):
            d04_201x = Date(y_d, 4, 1)
            with freezegun.freeze_time(d04_201x):
                assert_equals(YearMonth(2011, 4), _p(year=1), message=f'in {y_d}')

        for y_d in (2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030):
            d04_202x = Date(y_d, 4, 1)
            with freezegun.freeze_time(d04_202x):
                assert_equals(YearMonth(2021, 4), _p(year=1), message=f'in {y_d}')

    def test_can_check_for_equality(self):
        pic1 = PIC(year=2020, month=10, customer_id_short=23, counter=41)
        pic2 = PIC(*pic1)
        # explicit ==/!= to avoid assumptions about ordering/comparison#
        # operators used by PythonicTestcase
        assert_true(pic1 == pic2)
        # While "__ne__()" is implemented as "not __eq__()" by default in Python 3
        # namedtuple seems to define "__ne__()" explictly so PIC must override
        # that and we need to test that as well.
        assert_false(pic1 != pic2)

        for field_name in PIC._fields:
            other_pic = pic1._replace(**{field_name: 2})
            assert_true(pic1 != other_pic)
            assert_false(pic1 == other_pic)

        pic_2010 = pic1._replace(year=2010)
        pic_0 = pic1._replace(year=0)
        assert_true(pic_0 == pic1)
        assert_true(pic_0 == pic_2010)
        # ensure the code actually checks 4 digits if possible even though
        # that violates the principle of transitivity
        assert_true(pic_2010 != pic1)

    def test_can_other_pic_instances_within_same_month_and_customer(self):
        pic8 = PIC(year=2020, month=4, customer_id_short=6, counter=8)
        pic8a = PIC(*pic8)
        assert_false(pic8 < pic8a)
        assert_false(pic8a > pic8)
        assert_true(pic8a >= pic8)

        pic42 = pic8._replace(counter=42)
        assert_true(pic8 < pic42)
        assert_true(pic8 <= pic42)
        assert_false(pic8 > pic42)
        assert_true(pic42 > pic8)

        # checking incompatible fields
        for field_name in ('year', 'month', 'customer_id_short'):
            other_pic = pic8._replace(counter=9, **{field_name: 9})
            assert_true(pic8 != other_pic,
                message=f'{field_name}: 9 should not equal actual value {getattr(pic8, field_name)}')
            with assert_raises(NotImplementedError, message=f'PIC with {field_name}=9, counter=9 can not be compared to {repr(pic8)}'):
                pic8 < other_pic

        pic8_0 = pic8._replace(year=0, counter=9)
        assert_true( pic8   < pic8_0)
        assert_true( pic8  <= pic8_0)
        assert_false(pic8   > pic8_0)
        assert_true( pic8_0 > pic8)
        assert_false(pic8_0 < pic8)

        pic8_2010 = pic8._replace(year=2010, counter=9)
        with assert_raises(NotImplementedError, message=f'PIC {repr(pic8_2010)} can not be compared to {repr(pic8)}'):
            pic8 < pic8_2010

    def test_can_match_pic_string_with_expected_data(self):
        pic = PIC(YearMonth(2021, 2), customer_id_short=123, counter=54321)
        pic_str = str(pic)

        assert_true(pic_matches(pic_str, year=2021))
        assert_true(pic_matches(pic_str, year=1))
        assert_false(pic_matches(pic_str, year=2020))
        assert_false(pic_matches(pic_str, year=0))

        assert_true(pic_matches(pic_str, year=1, month=2))
        assert_false(pic_matches(pic_str, year=1, month=3))

        assert_true(pic_matches(pic_str, customer_id_short=123))
        assert_false(pic_matches(pic_str, customer_id_short=321))

        assert_true(pic_matches(pic_str, counter=54321))
        assert_false(pic_matches(pic_str, counter=12345))

    def test_can_shorten_long_pic_string(self):
        pic = PIC(YearMonth(2021, 2), customer_id_short=123, counter=54321)
        long_pic_str = pic.to_str(long_ik=True)
        short_pic_str = pic.to_str(long_ik=False)
        assert_equals(short_pic_str, shorten_long_pic_str(long_pic_str))

    def test_can_extend_short_pic_string(self):
        pic = PIC(YearMonth(2021, 2), customer_id_short=123, counter=54321)
        short_pic_str = pic.to_str(long_ik=False)
        long_pic_str = pic.to_str(long_ik=True)
        assert_equals(long_pic_str, extend_short_pic_str(short_pic_str))

