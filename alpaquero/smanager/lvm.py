#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Iterable, Collection, cast
import re
import os
import logging

from .storage_unit import LogicalVolume, CryptoVolume
from .storage_device import StorageDeviceOfLimitedSize
from .file_system import FSType
from .utils import get_block_device_size
from alpaquero.common.utils import run_cmd

if TYPE_CHECKING:
    from .manager import StorageManager
    from .storage_unit import Partition

log = logging.getLogger('smanager.lvm')


def contains_only_valid_lvm_chars(name: str) -> bool:
    if name in ('.', '..'):
        return False

    if not re.match(r'(?!-)[a-zA-Z0-9+_.-]+$', name):
        return False

    return True


def is_valid_vg_name(name: str) -> bool:
    if os.path.exists('/dev/{}'.format(name)):
        return False

    return contains_only_valid_lvm_chars(name)


def is_valid_lv_name(name: str) -> bool:
    if name in ('snapshot', 'pvmove'):
        return False

    prohibited_strings = ['_cdata', '_cmeta', '_corig', '_iorig',
                          '_mimage', '_mlog', '_pmspare', '_rimage',
                          '_rmeta', '_tdata', '_tmeta', '_vdata',
                          '_vorigin', '_wcorig']
    if any(word in name for word in prohibited_strings):
        return False

    return contains_only_valid_lvm_chars(name)


class VolumeGroup(StorageDeviceOfLimitedSize):
    def __init__(self, manager: StorageManager, id: str,
                 physical_volumes: Iterable[Partition | CryptoVolume]):
        """id must be volume group name"""

        if not is_valid_vg_name(id):
            raise ValueError('Invalid volume group name: {}'.format(id))

        size = 0
        for part in physical_volumes:
            if part.fs_type != FSType.PHYSICAL_VOLUME:
                raise ValueError('{} is not a physical volume partition')
            size += part.size
        if not size:
            raise ValueError('Empty physical volumes')

        self._physical_volumes = list(physical_volumes)
        self._logical_volumes: dict[str, LogicalVolume] = {}

        super().__init__(manager=manager, id=id, size=size)

    def __str__(self) -> str:
        return 'Volume group ({})'.format(self.id)

    @property
    def physical_volumes(self) -> Collection[Partition | CryptoVolume]:
        return self._physical_volumes[:]

    @property
    def logical_volumes(self) -> Collection[LogicalVolume]:
        return cast(Collection[LogicalVolume], self.storage_units)

    def add_lv(self, id: str, fs_type: Optional[FSType] = None,
               fs_opts: Optional[Iterable[str]] = None,
               size: int = 0, mount_point: Optional[str] = None) -> LogicalVolume:
        if not is_valid_lv_name(id):
            raise ValueError('Invalid logical volume name: {}'.format(id))
        opts = set()
        if fs_opts:
            opts = set(fs_opts)
        lv = LogicalVolume(id=id, size=size, fs_type=fs_type, fs_opts=opts,
                           mount_point=mount_point, storage_device=self)
        self._add_storage_unit(lv)
        log.debug('{}: added {}'.format(self, lv))
        return lv

    def create_logical_volumes(self):
        log.debug('{}: creating logical volumes'.format(self))
        args = ['vgcreate', self.id]
        args.extend(pv.block_device for pv in self.physical_volumes)
        run_cmd(args)

        for lv in self.logical_volumes:
            args = ['lvcreate', '-y', '-n', lv.id]
            if lv.use_all_available_space:
                args.extend(['--extents', '100%FREE'])
            else:
                args.extend(['--size', '{}m'.format(lv.size // (1024*1024))])
            args.append(self.id)
            run_cmd(args)

            lv.block_device = '/dev/{}/{}'.format(self.id, lv.id)
            lv.size = get_block_device_size(lv.block_device)

    def deactivate(self):
        run_cmd(args=['vgchange', '--activate', 'n', self.id])
