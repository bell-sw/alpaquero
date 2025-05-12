#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import logging
import abc
import os
import subprocess
from typing import Collection, Iterable, Optional

from alpaquero.common.utils import run_cmd, run_cmd_live
from alpaquero.common.events import EventReceiver

log = logging.getLogger('installer')


class InstallerException(Exception):
    pass


class Installer(abc.ABC):
    def __init__(self, name: str, config: dict,
                 target_root: str,
                 event_receiver: EventReceiver,
                 data_type,
                 data_is_optional: bool = False):
        self._name = name
        self._packages = set()
        self._target_root = target_root
        self._event_receiver = event_receiver

        self._data = config.get(name, None)
        if (not data_is_optional) and (self._data is None):
            raise InstallerException("'{}' is not set".format(name))
        if (self._data is not None) and (not isinstance(self._data, data_type)):
            raise InstallerException("'{}' is of type '{}', expected '{}'".format(
                name, type(self._data), data_type))

    @abc.abstractmethod
    def apply(self):
        pass

    def post_apply(self):
        pass

    def cleanup(self):
        pass

    @property
    def target_root(self) -> str:
        return self._target_root

    def pre_packages(self):
        return []

    @property
    def packages(self) -> Collection[str]:
        return set(self._packages)

    def add_package(self, *names: Collection[str]):
        self._packages.update(names)

    def abs_target_path(self, rel_target_path: str) -> str:
        return os.path.join(self.target_root,
                            rel_target_path.lstrip('/'))

    def run(self, args: list[str], input: Optional[bytes] = None) -> subprocess.CompletedProcess:
        return run_cmd(args=args, input=input, event_receiver=self._event_receiver)

    def run_in_chroot(self, args: list[str], input: Optional[bytes] = None) -> subprocess.CompletedProcess:
        new_args = ['chroot', self.target_root] + args
        return run_cmd(args=new_args, input=input, event_receiver=self._event_receiver)

    def enable_service(self, service: str, runlevel: str):
        self.run_in_chroot(args=['rc-update', 'add', service, runlevel])

    def disable_service(self, service: str, runlevel: str):
        # As disabling an already disabled service will exit with an error
        is_enabled = os.path.exists(os.path.join(self.abs_target_path('/etc/runlevels/'),
                                                 runlevel, service))
        if is_enabled:
            self.run_in_chroot(args=['rc-update', 'del', service, runlevel])
