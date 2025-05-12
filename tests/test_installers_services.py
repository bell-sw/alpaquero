#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import pytest

from alpaquero.installers.installer import InstallerException
from alpaquero.installers.services import ServicesInstaller
from .utils import new_installer


def create_installer(config: dict) -> ServicesInstaller:
    return new_installer(ServicesInstaller, config=config)


def test_no_services():
    create_installer({})
    create_installer({'services': {'enabled': []}})
    create_installer({'services': {'disabled': []}})


def test_invalid_services_type():
    with pytest.raises(InstallerException):
        create_installer({'services': False})


def test_invalid_list_format():
    for group in ('enabled', 'disabled'):
        label = f'services/{group}'
        with pytest.raises(ValueError, match=f'{label}'):
            create_installer({'services': {group: ['svc1', 'svc2', False]}})
