# -*- coding: UTF-8 -*-
# SPDX-License-Identifier: MIT or BSD-3-Clause

from collections import namedtuple
import itertools

from hexdump import hexdump
import colorama as _c

from srw.rdblib.testutil.colorama_helpers import colorama_color


__all__ = ['colorized_diff']

def colorized_diff(previous, current):
    lines_previous = hexdump(previous, result='generator')
    lines_current = hexdump(current, result='generator')
    for line_previous, line_current in itertools.zip_longest(lines_previous, lines_current):
        if line_previous == line_current:
            print('  ' + line_previous)
            continue
        diff_groups = find_differences(line_previous, line_current)
        previous = format_diff_line('-', line_previous, diff_groups)
        current = format_diff_line('+', line_current, diff_groups)
        print_diff_line(previous, is_previous=True)
        print_diff_line(current, is_previous=False)


def find_differences(line_a, line_b):
    diff_groups = []
    assert len(line_a) == len(line_b)
    diff_start = None
    diff_end = None

    def _add_as_diff_group():
        nonlocal diff_start, diff_end
        diff_groups.append((diff_start, diff_end))
        diff_start = None
        diff_end = None

    for c_idx, (c_a, c_b) in enumerate(zip(line_a, line_b)):
        if c_a == c_b:
            if diff_start is None:
                continue
            _add_as_diff_group()
        else:
            # c_a != c_b
            if diff_start is None:
                diff_start = c_idx
            diff_end = c_idx

    if diff_start is not None:
        _add_as_diff_group()

    return diff_groups


ChangeGroup = namedtuple('ChangeGroup', ('text', 'is_changed'))

def format_diff_line(prefix, line, diff_groups):
    parts = [
        ChangeGroup(prefix + ' ', is_changed=True),
    ]
    last_idx = -1
    for diff_group in diff_groups:
        start_idx, end_idx = diff_group
        if (start_idx != 0) and (last_idx != start_idx):
            unchanged_text = line[last_idx+1:start_idx]
            unchanged_group = ChangeGroup(unchanged_text, is_changed=False)
            parts.append(unchanged_group)

        text = line[start_idx:end_idx+1]
        cg = ChangeGroup(text, is_changed=True)
        parts.append(cg)
        last_idx = end_idx

    if last_idx + 1 < len(line):
        tail_idx = last_idx + 1
        tail_text = line[tail_idx:]
        cg = ChangeGroup(tail_text, is_changed=False)
        parts.append(cg)
    return parts

def print_diff_line(change_groups, *, is_previous=None):
    for cg in change_groups:
        if cg.is_changed:
            color = _c.Fore.RED if is_previous else _c.Fore.GREEN
            with colorama_color(color):
                print(cg.text, end='')
        else:
            print(cg.text, end='')
    print('\n', end='')

