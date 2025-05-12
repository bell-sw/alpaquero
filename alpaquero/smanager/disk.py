#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
from typing import TYPE_CHECKING
import os

from .storage_device import StorageDeviceWithPartitions
from .utils import get_block_device_size

if TYPE_CHECKING:
    from .manager import StorageManager


class Disk(StorageDeviceWithPartitions):
    def __init__(self, manager: StorageManager, id: str):
        """id must be block device name"""

        if not os.path.exists(id):
            raise ValueError("Device file '{}' does not exist".format(id))
        st = os.stat(id)
        if not os.path.stat.S_ISBLK(st.st_mode):
            raise ValueError("'{}' is not a block device file".format(id))

        super().__init__(manager=manager, id=id, size=get_block_device_size(id))

    def __str__(self) -> str:
        return 'Disk ({})'.format(self.id)
