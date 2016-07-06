# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals

from pythonic_testcase import *

from ddc.tool.storage.testhelpers import (
    batch_with_pic_forms, set_durus_loglevel, silence_durus_logging,
)
from ddc.tool.storage.pic_search import form_index_for_pic


class FormIndexForPICTest(PythonicTestCase):
    def setUp(self):
        super(FormIndexForPICTest, self).setUp()
        self._previous_loglevel = silence_durus_logging()

    def tearDown(self):
        set_durus_loglevel(self._previous_loglevel)
        super(FormIndexForPICTest, self).tearDown()

    def test_can_return_index_if_hint_is_spot_on(self):
        pic1 = '12345600100024'
        pic2 = '12345600114024'
        batch = batch_with_pic_forms([pic1, pic2])
        assert_equals(0, form_index_for_pic(batch, pic=pic1, index_hint=0))
        assert_equals(1, form_index_for_pic(batch, pic=pic2, index_hint=1))

    def test_can_handle_non_existing_pic(self):
        pic1 = '12345600100024'
        pic2 = '12345600114024'
        batch = batch_with_pic_forms([pic1, pic2])
        assert_none(form_index_for_pic(batch, pic='12345600000024', index_hint=1))

    def test_can_handle_index_hint_outside_of_valid_range(self):
        pic1 = '12345600100024'
        pic2 = '12345600114024'
        batch = batch_with_pic_forms([pic1, pic2])
        assert_equals(
            0,
            form_index_for_pic(batch, pic=pic1, index_hint=42),
            message='should find the right form even though the batch contains less than "index_hint" forms'
        )
        assert_equals(
            0,
            form_index_for_pic(batch, pic=pic1, index_hint=2),
            message='should find the right form even though the batch contains only 2 forms (max index = 1)'
        )
        assert_equals(
            1,
            form_index_for_pic(batch, pic=pic2, index_hint=-1),
            message='should find the right form even though the index_hint is negative'
        )

    def test_can_return_index_if_hint_is_past_actual_index(self):
        pic1 = '12345600100024'
        pic2 = '12345600101024'
        pic3 = '12345600114024'
        batch = batch_with_pic_forms([pic1, pic2, pic3])
        assert_equals(2, form_index_for_pic(batch, pic=pic3, index_hint=1))

    def test_can_return_index_if_hint_is_before_actual_index(self):
        pic1 = '12345600100024'
        pic2 = '12345600101024'
        pic3 = '12345600114024'
        batch = batch_with_pic_forms([pic1, pic2, pic3])
        assert_equals(1, form_index_for_pic(batch, pic=pic2, index_hint=2))

    def test_returns_no_match_if_form_is_deleted(self):
        pic1 = '12345600101024'
        pic2 = ('DELETED', '12345600114024')
        batch = batch_with_pic_forms([pic1, pic2])
        assert_none(form_index_for_pic(batch, pic=pic2[1], index_hint=1),
            message='index_hint is spot on')
        assert_none(form_index_for_pic(batch, pic=pic2[1], index_hint=0),
            message='index_hint is too low, need to scan')

    def test_can_return_index_of_deleted_form_if_specified(self):
        pic1 = '12345600101024'
        pic2 = ('DELETED', '12345600114024')
        pic3 = '12345600115024'
        batch = batch_with_pic_forms([pic1, pic2, pic3])
        assert_equals(
            1,
            form_index_for_pic(batch, pic=pic2[1],index_hint=0, ignore_deleted_forms=False),
            message='index_hint too low, need to scan'
        )
        assert_equals(
            1,
            form_index_for_pic(batch, pic=pic2[1],index_hint=1, ignore_deleted_forms=False),
            message='index_hint is spot on'
        )
        assert_equals(
            1,
            form_index_for_pic(batch, pic=pic2[1],index_hint=2, ignore_deleted_forms=False),
            message='index_hint too big, need to scan'
        )

    def test_returns_index_of_first_nondeleted_form_with_duplicate_pic_by_default(self):
        pic = '12345600114024'
        pic1 = ('DELETED', pic)
        pic2 = pic
        pic3 = '12345600115024'
        batch = batch_with_pic_forms([pic1, pic2, pic3])
        assert_equals(1, form_index_for_pic(batch, pic=pic, index_hint=0, ignore_deleted_forms=True),
            message='index_hint is too small')
        assert_equals(1, form_index_for_pic(batch, pic=pic, index_hint=1, ignore_deleted_forms=True),
            message='index_hint points to deleted form')
        assert_equals(1, form_index_for_pic(batch, pic=pic, index_hint=2, ignore_deleted_forms=True),
            message='index_hint points to correct form')

    def test_can_return_index_of_nondeleted_form_when_there_are_deleted_forms_with_the_same_pic(self):
        pic = '12345600114024'
        pic1 = '12345600110024'
        pic2 = ('DELETED', pic)
        pic3 = ('DELETED', pic)
        pic4 = pic
        pic5 = '12345600115024'
        batch = batch_with_pic_forms([pic1, pic2, pic3, pic4, pic5])

        # should return the index of the first non-deleted form
        assert_equals(3, form_index_for_pic(batch, pic=pic, index_hint=0, ignore_deleted_forms=False),
            message='index_hint is too small')
        assert_equals(3, form_index_for_pic(batch, pic=pic, index_hint=3, ignore_deleted_forms=False),
            message='index_hint is spot on')
        assert_equals(3, form_index_for_pic(batch, pic=pic, index_hint=4, ignore_deleted_forms=False),
            message='index_hint is too big')

