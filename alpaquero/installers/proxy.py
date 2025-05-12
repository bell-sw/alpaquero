#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import os

from .installer import Installer
from alpaquero.common.utils import validate_proxy_url, write_file

# Optional
#
# proxy: http://host:port
#


class ProxyInstaller(Installer):
    ENV_VARS = ('http_proxy', 'https_proxy')

    def __init__(self, target_root: str, config: dict, event_receiver):
        super().__init__(name='proxy', config=config,
                         event_receiver=event_receiver,
                         data_type=str, data_is_optional=True,
                         target_root=target_root)

        if self._data:
            validate_proxy_url(self._data)

    def apply(self):
        if not self._data:
            return

        self._event_receiver.start_event('Updating runtime proxy configuration')
        for v in self.ENV_VARS:
            os.environ[v] = self._data

    def post_apply(self):
        if not self._data:
            return

        self._event_receiver.start_event('Creating a proxy configuration file')
        lines = []
        for v in self.ENV_VARS:
            lines.append('export {}="{}"\n'.format(v, self._data))
        write_file(self.abs_target_path('/etc/profile.d/proxy.sh'), 'w',
                   data=''.join(lines))
