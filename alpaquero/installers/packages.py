#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from alpaquero.common.apk import APKManager
from .installer import Installer
from .utils import read_list

# Optional
#
# extra_packages: [ 'pkg1', 'pkg2' ]
#


class PackagesInstaller(Installer):
    def __init__(self, target_root: str, config: dict, event_receiver, apk: APKManager):
        yaml_tag = 'extra_packages'
        super().__init__(name=yaml_tag, config=config,
                         event_receiver=event_receiver,
                         target_root=target_root,
                         data_type=list,
                         data_is_optional=True)
        if self._data:
            extra_pkgs = read_list(config, key=yaml_tag, item_type=str,
                                   error_label=yaml_tag)
            for pkg in extra_pkgs:
                self.add_package(pkg)

        self._apk = apk

    def apply(self):
        self._event_receiver.start_event('Initializing APK database')
        self._apk.add(args=['--initdb'])

        self._event_receiver.start_event('Installing base packages:')
        self._apk.add(args=['distro-base'])

        if self.packages:
            self._event_receiver.start_event('Installing packages:')
            self._apk.add(args=self.packages)
