#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import os
import re

from alpaquero.common.utils import write_file
from .installer import Installer
from .utils import read_list

# Optional
#
# kernel:
#   cmdline: [ 'quiet' ]
#


class KernelInstaller(Installer):
    def __init__(self, target_root: str, config: dict, event_receiver):
        yaml_tag = 'kernel'
        super().__init__(name=yaml_tag, config=config,
                         event_receiver=event_receiver,
                         data_type=dict, data_is_optional=True,
                         target_root=target_root)

        self._cmdline: list[str] = []
        if self._data is not None:
            yaml_key = 'cmdline'
            self._cmdline = read_list(self._data, key=yaml_key, item_type=str,
                                      error_label=f'{yaml_tag}/{yaml_key}')

        self.add_package('linux-lts')

    def apply(self):
        pass

    def post_apply(self):
        self._event_receiver.start_event('Regenerating initrd')

        kver = None
        for name in os.listdir(self.abs_target_path('/boot')):
            m = re.match(r'^config-(\d+.*)$', name)
            if m:
                kver = m.group(1)
                break
        if not kver:
            raise RuntimeError('Unable to determine the installed kernel version')
        self.run_in_chroot(args=['dracut', '-f', f'/boot/initramfs-{kver}', kver])

        if self._cmdline:
            grub_path = self.abs_target_path('/etc/default/grub')
            data = ''
            with open(grub_path, 'r') as f:
                for line in f.readlines():
                    if line.startswith("GRUB_CMDLINE_LINUX_DEFAULT="):
                        line = 'GRUB_CMDLINE_LINUX_DEFAULT="{}"\n'.format(' '.join(self._cmdline))
                    data += line

            write_file(grub_path, 'w', data=data)
