#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
import enum


class FSType(enum.Enum):
    RAID_MEMBER = 1
    PHYSICAL_VOLUME = 2
    SWAP = 3
    EXT4 = 4
    XFS = 5
    VFAT = 6
    CRYPTO_PARTITION = 7

    @classmethod
    def from_str(cls, value: str) -> FSType:
        ret = getattr(cls, value.strip().upper(), None)
        if ret is None:
            raise ValueError('Unknown file system type: {}'.format(value))
        return ret

    def __str__(self) -> str:
        return self.name.lower()
