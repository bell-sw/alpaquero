#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import pytest

from alpaquero.common.apk import APKManager
from alpaquero.installers.installer import InstallerException
from alpaquero.installers.packages import PackagesInstaller
from .utils import new_installer, StubEventReceiver


def create_installer(config: dict) -> PackagesInstaller:
    event_receiver = StubEventReceiver()
    return new_installer(PackagesInstaller, config=config,
                         event_receiver=event_receiver,
                         apk=APKManager(event_receiver=event_receiver))


def test_no_extra_packages():
    installer = create_installer({})
    assert len(installer.packages) == 0


def test_invalid_extra_packages_type():
    with pytest.raises(InstallerException):
        create_installer({'extra_packages': False})


def test_invalid_extra_packages_list():
    with pytest.raises(ValueError):
        create_installer({'extra_packages': ['pkg1', False]})


def test_extra_packages():
    installer = create_installer({'extra_packages': ['pkg1', 'pkg2']})
    for pkg in ('pkg1', 'pkg2'):
        assert pkg in installer.packages
