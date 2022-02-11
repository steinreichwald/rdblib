
from collections import namedtuple
import re


__all__ = ['is_valid_batch_id', 'BatchID', 'BATCH_ID_REGEX']

BATCH_ID_REGEX = re.compile(r'^\d{8}$')


_BatchID = namedtuple('_BatchID', ('customer_id_long', 'batch_counter'))

class BatchID(_BatchID):
    @classmethod
    def from_str(cls, batch_id_str):
        assert is_valid_batch_id(batch_id_str), batch_id_str
        customer_id_long = int(batch_id_str[:5])
        batch_counter = int(batch_id_str[5:])
        return cls(customer_id_long=customer_id_long, batch_counter=batch_counter)

    @property
    def customer_str(self):
        str_ = f'{self.customer_id_long:05d}'
        assert len(str_) == 5, repr(self.customer_id_long)
        return str_

    @property
    def batch_counter_str(self):
        str_ = f'{self.batch_counter:03d}'
        assert len(str_) == 3, repr(self.batch_counter)
        return str_

    @property
    def counter(self):
        return self.batch_counter

    @property
    def pickup(self):
        return int(str(self.batch_counter)[0])

    def id_for_next_pickup(self):
        counter = (self.pickup + 1) * 100
        return BatchID(
            customer_id_long = self.customer_id_long,
            batch_counter    = counter,
        )

    def __str__(self):
        return f'{self.customer_str}{self.batch_counter_str}'

    def to_str(self):
        return str(self)

    def __add__(self, number):
        new_counter = self.batch_counter + number
        assert 100 <= new_counter < 999
        return self._replace(batch_counter=new_counter)

    def __sub__(self, number):
        assert (self.batch_counter % 100) != 0, 'never change to previous pickup'
        new_counter = self.batch_counter - number
        assert 100 <= new_counter < 999
        return self._replace(batch_counter=new_counter)


def is_valid_batch_id(batch_id_str):
    if (not batch_id_str) or (len(batch_id_str) != 8):
        return False
    elif not BATCH_ID_REGEX.match(batch_id_str):
        return False
    return True

