#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from typing import Optional

import pytest

from alpaquero.installers.installer import InstallerException
from alpaquero.installers.bootloader import BootloaderInstaller
from alpaquero.common.utils import Arch
from .utils import new_installer


def create_installer(config: dict, arch: Arch, efi_mount: Optional[str] = None) -> BootloaderInstaller:
    return new_installer(BootloaderInstaller, config=config, arch=arch, efi_mount=efi_mount)


def test_no_bootloader_device():
    with pytest.raises(ValueError, match="'bootloader_device'"):
        create_installer(config={}, arch=Arch.X86_64)


def test_non_efi_not_x86_64():
    with pytest.raises(ValueError, match="bootloader installation is not supported"):
        create_installer(config={}, arch=Arch.AARCH64)


def test_no_bootloader_device_with_efi():
    create_installer(config={}, arch=Arch.X86_64, efi_mount='/boot/efi')


def test_invalid_bootloader_device_type():
    with pytest.raises(InstallerException):
        create_installer(config={'bootloader_device': False}, arch=Arch.X86_64)


@pytest.mark.parametrize('arch', [Arch.X86_64, Arch.AARCH64])
def test_added_package_efi(arch):
    installer = create_installer(config={'bootloader_device': '/dev/vda'},
                                 arch=arch, efi_mount='/boot/efi')
    for pkg in ('grub', 'grub-efi'):
        assert pkg in installer.packages


def test_added_package_non_efi():
    installer = create_installer(config={'bootloader_device': '/dev/vda'}, arch=Arch.X86_64)
    for pkg in ('grub', 'grub-bios'):
        assert pkg in installer.packages
