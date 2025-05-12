#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from typing import Optional, Iterable, Collection, cast
import os
import logging

from .file_system import FSType
from .storage_unit import Partition, CryptoVolume
from .storage_device import StorageDevice

log = logging.getLogger('smanager.cryptsetup')

# Looking at the stock /etc/conf.d/dmcrypt it's not clear
# how to implement encrypted logical volumes, so as of now only
# regular partitions can be encrypted.


class Cryptsetup(StorageDevice):
    @property
    def volumes(self) -> Collection[CryptoVolume]:
        return cast(Collection[CryptoVolume], self.storage_units)

    def __str__(self) -> str:
        return 'Cryptsetup ({})'.format(self.id)

    def add_volume(self, id: str, partition: Partition,
                   fs_type: Optional[FSType] = None,
                   fs_opts: Optional[Iterable[str]] = None,
                   mount_point: Optional[str] = None) -> CryptoVolume:

        if not isinstance(partition, Partition):
            raise ValueError('{}: must be a partition'.format(partition))
        if partition.fs_type != FSType.CRYPTO_PARTITION:
            raise ValueError('{}: must be of the crypto partition type'.format(partition))

        block_device = os.path.join('/dev/mapper', id)
        if os.path.exists(block_device):
            raise ValueError('{}: block device already exists'.format(block_device))
        if self.get_unit_by_id(id):
            raise ValueError("A crypto volume with id '{}' already exists".format(id))

        opts = set()
        if fs_opts:
            opts = set(fs_opts)
        volume = CryptoVolume(id=id, size=partition.size, fs_type=fs_type, fs_opts=opts,
                              mount_point=mount_point, storage_device=self,
                              partition=partition)
        volume.block_device = block_device

        self._add_storage_unit(volume)
        log.debug('{}: added {}'.format(self, volume))
        return volume

    def open_volumes(self):
        log.debug('{}: opening volumes'.format(self))
        for volume in self.volumes:
            volume.open()

    def close_volumes(self):
        for volume in self.volumes:
            volume.close()
