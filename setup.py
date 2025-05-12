#!/usr/bin/env python3

#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import setuptools

setuptools.setup(
    name='alpaquero',
    version="0.8.4",
    description="Installer for Alpaquita-like Linux distributions",
    long_description="",
    author='BellSoft',
    author_email='info@bell-sw.com',
    url='https://bell-sw.com',
    license="AGPLv3+",
    install_requires=['attrs', 'PyYAML', 'urwid'],
    packages=setuptools.find_packages(
        exclude=['subiquitycore.tests',
                 'subiquitycore.ui.tests',
                 'subiquitycore.ui.views.tests',
                 'tests']
    ),
    package_data={
        'alpaquero': ['EULA', 'keys/**/*'],
    },
    scripts=[
          'bin/alpaquero',
        ],
    )
