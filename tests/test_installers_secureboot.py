#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import pytest

from alpaquero.common.apk import APKManager
from alpaquero.installers.installer import InstallerException
from alpaquero.installers.secureboot import SecureBootInstaller
from .utils import new_installer, StubEventReceiver


def create_installer(config: dict) -> SecureBootInstaller:
    event_receiver = StubEventReceiver()
    return new_installer(SecureBootInstaller, config=config,
                         event_receiver=event_receiver,
                         apk=APKManager(event_receiver=event_receiver))


def test_no_install_shim_bootloader():
    create_installer({})


def test_invalid_install_shim_bootloader_type():
    with pytest.raises(InstallerException):
        create_installer({'install_shim_bootloader': ''})


def test_added_packages():
    installer = create_installer({'install_shim_bootloader': True})
    for pkg in ('sbsigntool', 'efitools', 'mokutil'):
        assert pkg in installer.packages
