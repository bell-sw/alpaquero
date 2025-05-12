#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
from typing import TYPE_CHECKING, Iterable, Collection
import os
import re
import logging

from .storage_device import StorageDeviceWithPartitions
from .storage_unit import Partition, CryptoVolume
from .file_system import FSType
from alpaquero.common.utils import run_cmd

if TYPE_CHECKING:
    from .manager import StorageManager

log = logging.getLogger('smanager.raid')

RAID_ID_PATTERN = r'/dev/md/[a-z0-9-_]+'


class RAID(StorageDeviceWithPartitions):
    def __init__(self, manager: StorageManager, id: str,
                 level: int, members: Iterable[Partition | CryptoVolume],
                 metadata: str = '1.2'):
        """id must be of format /dev/md/<raid_name>"""

        # Note, that other levels will require implementing
        # stride and stripe-width attributes plus a more
        # sophisticated logic for determining the available size.
        if level != 1:
            raise ValueError('Only RAID1 is supported')
        self._level = level

        if not re.match(RAID_ID_PATTERN, id):
            raise ValueError("RAID id '{}' does not match format '{}'".format(id, RAID_ID_PATTERN))

        if metadata not in ('1.0', '1.1', '1.2'):
            raise ValueError("Metadata {} is not supported".format(metadata))
        self._metadata = metadata

        self._members = list(members)
        if len(self._members) < 2:
            raise ValueError('Provide at least 2 RAID members')
        if any(m.fs_type != FSType.RAID_MEMBER for m in members):
            raise ValueError('All members must be of the RAID type')
        if any(not isinstance(m, (Partition, CryptoVolume)) for m in members):
            raise ValueError('All members must be of the Partition or CryptoVolume types')
        size = min(m.size for m in members)

        self._raid_created = False

        super().__init__(manager=manager, id=id, size=size)
        self._block_device = None

    def __str__(self) -> str:
        return 'RAID {} on {}'.format(self.id, ','.join(str(m) for m in self.members))

    @property
    def members(self) -> Collection[Partition]:
        return self._members[:]

    @property
    def level(self) -> int:
        return self._level

    @property
    def metadata(self) -> str:
        return self._metadata

    def create(self):
        if self._raid_created:
            return
        log.debug('{}: initialising'.format(self))

        args = ['mdadm', '--create', '-f',
                '--metadata={}'.format(self.metadata),
                '--run', '--homehost=any',
                '--level={}'.format(self.level),
                '--raid-devices={}'.format(len(self.members)),
                self.id]
        args.extend(m.block_device for m in self.members)
        run_cmd(args)

        self._block_device = os.path.realpath(self.id)
        self._raid_created = True

    def create_partitions(self):
        self.create()
        super().create_partitions()

    def stop(self):
        run_cmd(args=['mdadm', '--stop', self.id])
