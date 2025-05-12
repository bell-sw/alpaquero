#  SPDX-FileCopyrightText: 2023 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import os
from typing import Iterable, Optional

from alpaquero.common.utils import run_cmd_live, write_file
from alpaquero.common.events import EventReceiver


class APKManager:
    def __init__(self, event_receiver: EventReceiver):
        self._event_receiver = event_receiver

        self.keys_dir = '/etc/apk/keys'
        self.root_dir = None

    @staticmethod
    def _dir_exists(d: str):
        if not os.path.isdir(d):
            raise ValueError(f"'{d}' is not a directory")

    @staticmethod
    def _transform_apk_add(txt: str):
        if 'Installing' in txt:
            return ' * ' + txt.replace('Installing ', '')
        if txt.startswith('ERROR:'):
            return '   ' + txt
        return None

    def _get_apk_dir(self):
        if self._root_dir is None:
            root_dir = '/'
        else:
            root_dir = self._root_dir
        return os.path.join(root_dir, 'etc/apk')

    def _get_repo_file_path(self):
        return os.path.join(self._get_apk_dir(), 'repositories')

    @property
    def keys_dir(self) -> Optional[str]:
        return self._keys_dir

    @keys_dir.setter
    def keys_dir(self, val: Optional[str]):
        if val is not None:
            self._dir_exists(val)
        self._keys_dir = val

    @property
    def root_dir(self) -> Optional[str]:
        return self._root_dir

    @root_dir.setter
    def root_dir(self, val: Optional[str]):
        if val is not None:
            self._dir_exists(val)
        self._root_dir = val

    def write_repo_file(self, data):
        repo_file = self._get_repo_file_path()
        os.makedirs(os.path.dirname(repo_file), exist_ok=True)
        write_file(repo_file, 'w', data=data)

    def read_repo_file(self):
        with open(self._get_repo_file_path(), 'r') as file:
            return file.read()

    def add(self, args: Iterable):
        all_args = ['apk', 'add', '--no-progress', '--update-cache', '--clean-protected']
        if self.root_dir is not None:
            all_args.extend(['--root', self.root_dir])
        if self.keys_dir is not None:
            all_args.extend(['--keys-dir', self.keys_dir])
        all_args.extend(args)
        run_cmd_live(args=all_args, event_receiver=self._event_receiver,
                     event_transform=self._transform_apk_add)
