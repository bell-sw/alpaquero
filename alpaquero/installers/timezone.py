#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import os

from alpaquero.models.timezone import REGIONS, ZONEINFO_DIR
from .installer import Installer, InstallerException

#
# timezone: America/New_York
#


class TimezoneInstaller(Installer):
    def __init__(self, target_root: str, config: dict, event_receiver):
        super().__init__(name='timezone', config=config,
                         event_receiver=event_receiver,
                         data_type=str, target_root=target_root)

        self._timezone = self._data.strip()
        tokens = self._timezone.split('/')
        if (len(tokens) < 2) or (tokens[0] not in REGIONS):
            raise InstallerException("Invalid timezone specification: {}".format(self._timezone))

        self.add_package('tzdata')

    def apply(self):
        self._event_receiver.start_event('Configuring time zone')
        zone_path_rel = os.path.join(ZONEINFO_DIR, self._timezone)
        zone_path_abs = self.abs_target_path(zone_path_rel)

        if not os.path.exists(zone_path_abs):
            raise InstallerException("Zone file does not exist: {}".format(zone_path_abs))

        localtime_abs = os.path.join(self.target_root, 'etc/localtime')
        self._event_receiver.add_log_line("Creating a symlink /etc/localtime pointing to '{}'".format(
            zone_path_rel))
        os.symlink(src=zone_path_rel, dst=localtime_abs)
