#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import pytest

from alpaquero.installers.installer import InstallerException
from alpaquero.installers.proxy import ProxyInstaller
from .utils import new_installer


def create_installer(config: dict) -> ProxyInstaller:
    return new_installer(ProxyInstaller, config=config)


def test_no_proxy():
    create_installer({})


def test_proxy_invalid_type():
    with pytest.raises(InstallerException):
        create_installer({'proxy': False})


def test_invalid_proxy_url():
    # validate_proxy_url is tested independently, so here is just a short check
    # that an invalid url leads to an exception
    urls = ['https://domain.com',
            'http://',
            'domain.com',
            ]
    for url in urls:
        with pytest.raises(ValueError):
            create_installer({'proxy': url})


def test_valid_proxy_url():
    urls = ['http://domain.com',
            'http://domain.com:4351']
    for url in urls:
        create_installer({'proxy': url})
