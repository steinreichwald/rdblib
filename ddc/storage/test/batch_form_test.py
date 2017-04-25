# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from pythonic_testcase import *

from ddc.storage.testhelpers import batch_with_pic_forms


class BatchFormTest(PythonicTestCase):
    def test_can_retrieve_pic_for_form(self):
        pic1 = '12345600100024'
        pic2 = '12345600114024'
        batch = batch_with_pic_forms([pic1, pic2])
        assert_equals(pic1, batch.batch_form(0).pic())
        assert_equals(pic2, batch.batch_form(1).pic())

