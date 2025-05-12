#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import pytest

from alpaquero.installers.installer import InstallerException
from alpaquero.installers.timezone import TimezoneInstaller
from .utils import new_installer


def create_installer(config: dict) -> TimezoneInstaller:
    return new_installer(TimezoneInstaller, config=config)


def test_no_timezone():
    with pytest.raises(InstallerException, match='is not set'):
        create_installer({})


def test_invalid_timezone_type():
    with pytest.raises(InstallerException):
        create_installer({'timezone': False})


def test_invalid_timezone():
    for config in [{'timezone': 'INVALID_REGION/Los_Angeles'},
                   {'timezone': 'Europe'}]:
        with pytest.raises(InstallerException, match=r'(?i)invalid timezone'):
            create_installer(config)


def test_packages():
    installer = create_installer({'timezone': 'America/New_York'})
    assert 'tzdata' in installer.packages
