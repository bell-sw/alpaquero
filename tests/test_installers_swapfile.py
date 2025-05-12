#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import pytest

from alpaquero.installers.installer import InstallerException
from alpaquero.installers.swapfile import SwapfileInstaller
from .utils import new_installer


def create_installer(config: dict) -> SwapfileInstaller:
    return new_installer(SwapfileInstaller, config=config)


def test_no_swap_file():
    create_installer({})


def test_invalid_swap_file_type():
    with pytest.raises(InstallerException):
        create_installer({'swap_file': False})


def test_missing_tags():
    config = {'swap_file': ''}

    with pytest.raises(InstallerException):
        create_installer(config)

    with pytest.raises(ValueError, match="'swap_file/size'"):
        config['swap_file'] = {'path': 'some_path'}  # type: ignore
        create_installer(config)

    with pytest.raises(ValueError, match="'swap_file/path'"):
        config['swap_file'] = {'size': '2M'}
        create_installer(config)


def test_invalid_size():
    config = {'swap_file': {'path': '/some/path', 'size': 'X'}}
    with pytest.raises(ValueError, match=r'(?i)invalid size'):
        create_installer(config)


def test_small_size():
    with pytest.raises(ValueError, match="is less than 1M"):
        config = {'swap_file': {'path': '/some/path', 'size': '10K'}}
        create_installer(config)
