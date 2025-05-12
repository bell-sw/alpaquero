
#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from .installer import Installer
from alpaquero.common.apk import APKManager

# Optional
#
# install_shim_bootloader: true
#


class SecureBootInstaller(Installer):
    def __init__(self, target_root: str, config: dict, event_receiver, apk: APKManager):
        super().__init__(name='install_shim_bootloader', config=config,
                         event_receiver=event_receiver,
                         data_type=bool, target_root=target_root,
                         data_is_optional=True)

        if not self._data:
            return

        self._apk = apk
        self.add_package('sbsigntool', 'efitools', 'mokutil')

    def apply(self):
        pass

    def post_apply(self):
        if not self._data:
            return
        self._event_receiver.start_event('Installing shim and grub-efi-signed bootloaders:')
        self._apk.add(args=['shim-signed', 'grub-efi-signed'])
