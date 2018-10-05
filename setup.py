#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys

if sys.version_info < (3,3):
    sys.stderr.write('setup.py must be run with Python 3.3+.\n')
    sys.exit(1)

def requires_from_file(filename):
    requirements = []
    with open(filename, 'r') as requirements_fp:
        for line in requirements_fp.readlines():
            match = re.search('^\s*([a-zA-Z][^#]+?)(\s*#.+)?\n$', line)
            if match:
                requirements.append(match.group(1))
    return requirements

from setuptools import setup, find_packages


setup(
    name='rdblib',
    version='1.1',
    license = '3-clause BSD',
    packages=find_packages(),
    namespace_packages = ['srw'],
    include_package_data=True,
    install_requires=requires_from_file('requirements.txt'),

    entry_points = {
        'console_scripts': [
            'srw-extract-image = srw.rdblib.cli:extract_image_main',
        ]
    },
)

