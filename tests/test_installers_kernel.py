#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import pytest

from alpaquero.installers.installer import InstallerException
from alpaquero.installers.kernel import KernelInstaller
from .utils import new_installer


def create_installer(config: dict) -> KernelInstaller:
    return new_installer(KernelInstaller, config=config)


def test_no_kernel():
    create_installer({})


def test_invalid_kernel_type():
    with pytest.raises(InstallerException):
        create_installer({'kernel': False})


def test_invalid_cmdline():
    label = 'kernel/cmdline'
    for cmdline in (False, ['opt1', 'opt2', True]):
        with pytest.raises(ValueError, match=f"'{label}'"):
            create_installer({'kernel': {'cmdline': cmdline}})


def test_added_packages():
    installer = create_installer({'kernel': {'cmdline': ['opt1', 'opt2']}})
    assert 'linux-lts' in installer.packages
