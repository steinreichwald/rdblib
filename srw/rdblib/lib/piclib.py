
from collections import namedtuple
from datetime import date as Date

from .yearmonth import YearMonth



__all__ = [
    'extend_short_pic_str',
    'generate_pic_str',
    'pic_matches',
    'shorten_long_pic_str',
    'PIC',
]

IK_RZ_SHORT = '024'
IK_RZ_LONG = f'0000{IK_RZ_SHORT}'

_PIC = namedtuple('_PIC', ('year', 'month', 'customer_id_short', 'counter'))
_PIC.__new__.__defaults__ = (
    None,       # counter
)

class PIC(_PIC):
    def __new__(cls, *args, **kwargs):
        if args:
            year = args[0]
            param_count = len(kwargs) + len(args)
            field_count = len(cls._fields)
            is_month_set = (param_count >= field_count) or ('month' in kwargs)
            if (not is_month_set) and hasattr(year, 'month'):
                args = (year.year, year.month, *args[1:])
        return super().__new__(cls, *args, **kwargs)

    def __str__(self):
        return self.to_str()

    def to_str(self, rz_ik_separator=None, long_ik=False):
        return generate_pic_str(**self.as_dict(), rz_ik_separator=rz_ik_separator, long_ik=long_ik)

    @classmethod
    def from_str(cls, pic_str):
        assert len(pic_str) in (14, 18), pic_str
        is_short_ik = (len(pic_str) == 14)
        rz_ik = pic_str[11:]
        expected_ik = IK_RZ_SHORT if is_short_ik else IK_RZ_LONG
        assert rz_ik == expected_ik, pic_str
        return cls(
            year              = int(pic_str[0]),
            month             = int(pic_str[1:3]),
            customer_id_short = int(pic_str[3:6]),
            counter           = int(pic_str[6:11])
        )

    def as_dict(self):
        return dict(zip(self._fields, self))

    def guess_year_month(self):
        is_one_digit_year = (len(str(self.year)) == 1)
        if not is_one_digit_year:
            return YearMonth(year=self.year, month=self.month)

        current_year = Date.today().year
        decade_year = int(str(current_year)[:3] + '0')
        guessed_year = decade_year + self.year
        if guessed_year > current_year:
            guessed_year -= 10
        return YearMonth(guessed_year, month=self.month)

    def __add__(self, number):
        new_counter = self.counter + number
        assert 0 <= new_counter < 99999
        return self._replace(counter=new_counter)

    def __eq__(self, other):
        for field_name in self._fields:
            if not hasattr(other, field_name):
                return NotImplemented

        if not self._is_same_year(other):
            return False
        elif self.month != other.month:
            return False
        elif self.customer_id_short != other.customer_id_short:
            return False
        return (self.counter == other.counter)

    def _is_same_year(self, other):
        self_is_one_digit_year = (len(str(self.year)) == 1)
        other_is_one_digit_year = (len(str(other.year)) == 1)
        self_year = self.year
        other_year = other.year
        if self_is_one_digit_year:
            other_year = int(str(other.year)[-1])
        elif other_is_one_digit_year:
            self_year = int(str(self.year)[-1])
        return (self_year == other_year)

    # need to override implementation from namedtuple
    def __ne__(self, other):
        return not (self == other)

    def __lt__(self, other):
        # regarding the use of NotImplemented:
        #   https://stackoverflow.com/a/44575926/138526
        #   https://stackoverflow.com/a/879005/138526
        # However Python got stuck into endless recursion when returning only
        # NotImplemented so I decided to raise NotImplementedError.
        # In the end the PIC class is completely custom and I don't see the
        # need to use it anywhere else.
        for field_name in self._fields:
            if not hasattr(other, field_name):
                raise NotImplementedError(f'{repr(other)} has no field {field_name}')

        if not self._is_same_year(other):
            raise NotImplementedError()
        elif self.month != other.month:
            raise NotImplementedError()
        elif self.customer_id_short != other.customer_id_short:
            raise NotImplementedError()

        return (self.counter < other.counter)

    def __le__(self, other):
        return (self == other) or (self < other)

    # need to override implementation from namedtuple
    def __gt__(self, other):
        if self == other:
            return False
        elif self < other:
            return False
        return True

    def __ge__(self, other):
        return (self == other) or (self > other)

    def __hash__(self):
        return hash(str(self))


def shorten_long_pic_str(long_pic_str):
    "Convert a 18-digit PIC to a 14-digit PIC in performance-optimized way."
    assert isinstance(long_pic_str, str)
    assert len(long_pic_str) == 18
    assert long_pic_str.endswith(IK_RZ_LONG)
    pic_base = long_pic_str[:-len(IK_RZ_LONG)]
    short_pic_str = pic_base + IK_RZ_SHORT
    return short_pic_str

def extend_short_pic_str(short_pic_str):
    "Convert a 14-digit PIC to a 18-digit PIC in performance-optimized way."
    assert isinstance(short_pic_str, str)
    assert len(short_pic_str) == 14
    assert short_pic_str.endswith(IK_RZ_SHORT)
    assert not short_pic_str.endswith(IK_RZ_LONG)
    pic_base = short_pic_str[:-len(IK_RZ_SHORT)]
    return pic_base + IK_RZ_LONG

def pic_matches(pic_str, *, year=None, month=None, customer_id_short=None, counter=None):
    if not isinstance(pic_str, str):
        pic = pic_str
        pic_str = str(pic)

    # YearMonth support
    if hasattr(year, 'month') and (month is None):
        month = year.month
        year = year.year
    elif hasattr(month, 'year') and (year is None):
        year = month.year
        month = month.month

    if year is not None:
        year_str = pic_str[0]
        if year_str != nr2str(year, length=4)[-1]:
            return False
    if month is not None:
        month_str = pic_str[1:3]
        if month_str != nr2str(month, length=2):
            return False
    if customer_id_short is not None:
        c_str = pic_str[3:6]
        if c_str != nr2str(customer_id_short, length=3):
            return False
    if counter is not None:
        counter_str = pic_str[6:11]
        if counter_str != nr2str(counter, length=5):
            return False
    if not pic_str.endswith(IK_RZ_SHORT):
        return False
    return True


def generate_pic_str(*, year, month, customer_id_short, counter=None, rz_ik_separator=None, long_ik=None):
    year_digit = nr2str(year, length=4)[-1]
    months_digits = nr2str(month, length=2, default='?')
    customer_str = nr2str(customer_id_short, length=3)
    counter_str = nr2str(counter, length=5, default='#')
    rz_ik_separator = (rz_ik_separator or '')
    ik_rz = IK_RZ_LONG if long_ik else IK_RZ_SHORT
    return f'{year_digit}{months_digits}{customer_str}{counter_str}{rz_ik_separator}{ik_rz}'

def nr2str(value, length, default=None):
    if isinstance(value, bytes):
        value = value.decode('ASCII')
    if isinstance(value, str):
        nr_str = value
    elif (value is None) and (default is not None):
        nr_str = default * length
    else:
        fmt = '%%0%dd' % length
        nr_str = fmt % value
    assert len(nr_str) == length, f'"{nr_str}" must have {length} characters'
    return nr_str

