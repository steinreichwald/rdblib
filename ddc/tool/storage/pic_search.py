# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, print_function, unicode_literals


__all__ = ['form_index_for_pic']

def form_index_for_pic(batch, *, pic, index_hint, ignore_deleted_forms=True):
    also_return_deleted_forms = not ignore_deleted_forms
    form_count = len(batch.forms())
    # ensure that 0 <= i <= form_count
    limit_index = lambda i: max(0, min(i, form_count - 1))
    current_index = limit_index(index_hint)

    form = batch.form(current_index)
    hinted_pic = batch.pic_for_form(current_index)
    # We have to deal with duplicate PICs in a batch. However all forms but one
    # MUST be marked as "deleted" so there is only a single non-deleted form for a
    # given PIC.
    # Even if we don't ignore deleted forms we should still prefer non-deleted
    # forms over deleted forms with the same PIC. (Usually the deleted ones were
    # bad scans so they are not very useful). If there are only deleted forms for
    # a given PIC, return the one with the highest index.
    last_index_for_pic = None
    if pic == hinted_pic:
        if not form.is_deleted():
            return current_index
        elif also_return_deleted_forms:
            last_index_for_pic = current_index

    # the <index_hint> might be a bit of (mostly due to deleted forms which our
    # backend system might not know) so we need to scan the CDB file.
    # (Note July 2016: The following optimization is likely not really necessary
    # anymore as the network should be fast enough to load all batch-related data.
    # However the code is there and it is not really complicated so why not use it?)
    #
    # To minimize the number of checked forms we can optimize that as the
    # PIC numbers in the batch are ALWAYS in ascending order.
    # That means so we can safely search forward, if the PIC at <index_hint> is
    # lower than the requested <pic>, and search backwards if the PIC at
    # <index_hint> is greater than the requested <pic>
    #
    # this should minimize the network traffic compared to the previous
    # solution "for i in range(seq.form_count)" - in the worst case we
    # had to load 300 form-headers to find the right form (<index_hint> is 299,
    # but 300 is the form with the requested <pic>)
    if hinted_pic < pic:
        # search forward if the pic at <index_hint> is lower than <pic>
        start_nr = current_index + 1
        stop_nr = start_nr + form_count
        step = 1
    else:
        # search backward if the pic at <index_hint> is greater than <pic>
        start_nr = current_index - 1
        stop_nr = start_nr - form_count # -1 so because range() should also emit 0 (and stop_nr is exclusive)
        step = -1
    for raw_index in range(start_nr, stop_nr, step):
        # add a comment about wrappping, scanning all forms
        current_index = raw_index % form_count
        assert 0 <= current_index < form_count, 'out of bounds: current_index=%r' % current_index
        current_pic = batch.pic_for_form(current_index)
        form = batch.form(current_index)
        if pic == current_pic:
            is_form_more_recent = (last_index_for_pic is None) or (current_index > last_index_for_pic)
            if not form.is_deleted():
                return current_index
            elif also_return_deleted_forms and is_form_more_recent:
                last_index_for_pic = current_index
    return last_index_for_pic

