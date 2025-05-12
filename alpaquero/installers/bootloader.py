#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import os

from alpaquero.app.distro import DISTRO
from alpaquero.common.utils import Arch
from .installer import Installer
from typing import Optional

# Required for non-EFI installations
#
# bootloader_device: /dev/vdX
#


class BootloaderInstaller(Installer):
    def __init__(self, target_root: str, config: dict, event_receiver,
                 arch: Arch, efi_mount: Optional[str]):
        yaml_key = 'bootloader_device'
        super().__init__(name=yaml_key, config=config,
                         event_receiver=event_receiver,
                         data_type=str, data_is_optional=True,
                         target_root=target_root)

        self._arch = arch
        self._efi_mount = efi_mount
        if self._efi_mount:
            self.add_package('grub', 'grub-efi')
        else:
            if self._arch != Arch.X86_64:
                raise ValueError(f"Non-EFI bootloader installation is not supported on {self._arch}")

            if (not self._data) or (not isinstance(self._data, str)):
                raise ValueError("There must be an '{}' entry of type string".format(yaml_key))
            self.add_package('grub', 'grub-bios')

    def apply(self):
        pass

    def post_apply(self):
        self._event_receiver.start_event('Installing bootloader')
        self.run_in_chroot(args=['grub-mkconfig', '-o', '/boot/grub/grub.cfg'])
        if self._efi_mount:
            target = {Arch.X86_64: "x86_64-efi", Arch.AARCH64: "arm64-efi"}[self._arch]
            grub64_efi = {Arch.X86_64: "grubx64.efi", Arch.AARCH64: "grubaa64.efi"}[self._arch]
            boot64_efi = {Arch.X86_64: "bootx64.efi", Arch.AARCH64: "bootaa64.efi"}[self._arch]

            self.run_in_chroot(args=['grub-install', f"--target={target}",
                                     '--efi-directory={}'.format(self._efi_mount),
                                     '--boot-directory=/boot', f'--bootloader-id={DISTRO}',
                                     '--no-nvram'])
            self.run_in_chroot(args=['install', '-D',
                                     os.path.join(self._efi_mount, f"EFI/{DISTRO}/{grub64_efi}"),
                                     os.path.join(self._efi_mount, f"EFI/boot/{boot64_efi}")])
        else:
            self.run_in_chroot(args=['grub-install', '--target=i386-pc',
                                     '--boot-directory=/boot', self._data])
