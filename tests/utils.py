#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from typing import Type, TypeVar

from alpaquero.common.events import EventReceiver


class StubEventReceiver(EventReceiver):
    def __init__(self):
        self._event_lines = []
        self._log_lines = []

    @property
    def event_lines(self):
        return list(self._event_lines)

    @property
    def log_lines(self):
        return list(self._log_lines)

    def start_event(self, msg):
        self._event_lines.append(msg)

    def stop_event(self):
        pass

    def add_log_line(self, msg):
        self._log_lines.append(msg)


_InstallerType = TypeVar('_InstallerType')


def new_installer(installer_cls: Type[_InstallerType], **kwargs) -> _InstallerType:
    if 'target_root' not in kwargs:
        kwargs['target_root'] = 'target_root'
    if 'event_receiver' not in kwargs:
        kwargs['event_receiver'] = StubEventReceiver()
    return installer_cls(**kwargs)
