#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import os
import stat
from typing import Optional

from alpaquero.common.utils import write_file
from .installer import Installer
from .utils import read_key_or_fail, str_size_to_bytes

# Optional
#
# swap_file:
#    path: /swapfile
#    size: 512M


class SwapfileInstaller(Installer):
    def __init__(self, target_root: str, config: dict, event_receiver):
        yaml_tag='swap_file'
        super().__init__(name=yaml_tag, config=config,
                         event_receiver=event_receiver,
                         data_type=dict, data_is_optional=True,
                         target_root=target_root)

        self._path: Optional[str] = None
        self._size = 0

        if self._data is None:
            return

        yaml_path_key = 'path'
        self._path = read_key_or_fail(self._data, yaml_path_key, str,
                                      error_label=f'{yaml_tag}/{yaml_path_key}')
        if not self._path:
            raise ValueError(f"No '{yaml_tag}/{yaml_path_key}' is specified")
        self._path = os.path.join('/', self._path.lstrip('/'))

        yaml_size_key = 'size'
        size = self._data.get(yaml_size_key, None)
        if size is None:
            raise ValueError(f"No '{yaml_tag}/{yaml_size_key}' is specified")
        try:
            size_in_bytes = str_size_to_bytes(str(size))
        except ValueError as exc:
            raise ValueError('{}/{}: {}'.format(yaml_tag, yaml_size_key, str(exc))) from None
        # We keep the self._size in megabytes
        self._size = size_in_bytes // (1024 * 1024)
        if not self._size:
            raise ValueError('Swap file size {} is less than 1M'.format(size_in_bytes))

    def apply(self):
        if not self._path:
            return

        self._event_receiver.start_event('Creating swap file')
        abs_path = self.abs_target_path(self._path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        self.run_in_chroot(args=['dd', 'if=/dev/zero', 'of={}'.format(self._path),
                                 'bs=1M', 'count={}'.format(self._size)])
        os.chown(abs_path, 0, 0)
        os.chmod(abs_path, stat.S_IRUSR | stat.S_IWUSR)
        self.run_in_chroot(args=['mkswap', self._path])

    def post_apply(self):
        if not self._path:
            return

        write_file(self.abs_target_path('/etc/fstab'), 'a',
                   data='{} swap swap defaults 0 0\n'.format(self._path))
