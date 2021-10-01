

from pythonic_testcase import *

from ..batchlib import BatchID


class BatchIDTest(PythonicTestCase):
    def test_str(self):
        batch_id = BatchID(customer_id_long=123, batch_counter=107)
        assert_equals('00123107', batch_id.to_str())
        assert_equals('00123107', str(batch_id))

    def test_from_str(self):
        batch_id = BatchID(customer_id_long=123, batch_counter=107)
        batch_id_str = str(batch_id)
        assert_equals(batch_id, BatchID.from_str(batch_id_str))

    def test_can_increment_counter(self):
        batch_id = BatchID(customer_id_long=123, batch_counter=107)
        new_batch_id = batch_id + 1
        assert_equals(batch_id._replace(batch_counter=108), new_batch_id)

