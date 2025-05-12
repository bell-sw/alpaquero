#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import os

import pytest

from alpaquero.common.utils import run_cmd
from alpaquero.smanager.manager import StorageManager
from alpaquero.smanager.file_system import FSType

MB = 1024 * 1024


@pytest.fixture(scope='session')
def test_disk():
    res = os.getenv('TEST_DISK', None)
    if res is None:
        pytest.skip("Please set the 'TEST_DISK' variable before running the tests."
                    " All data there will be destroyed.")
    return res


def test_create_filesystems(test_disk):
    repeat_count = 50

    print('test_disk is {}'.format(test_disk))

    layout1 = [{'id': 'part1', 'fs_type': FSType.EXT4, 'size': 300*MB, 'mount_point': '/part1'}]
    layout2 = [{'id': 'part1', 'fs_type': FSType.EXT4, 'size': 100*MB, 'mount_point': '/part1'},
              {'id': 'part2', 'fs_type': FSType.EXT4, 'size': 200*MB, 'mount_point': '/part2'}]
    layout3 = [{'id': 'part1', 'fs_type': FSType.EXT4, 'size': 100*MB, 'mount_point': '/part1'},
               {'id': 'part2', 'fs_type': FSType.EXT4, 'size': 100*MB, 'mount_point': '/part2'},
               {'id': 'part3', 'fs_type': FSType.EXT4, 'size': 100*MB, 'mount_point': '/part3'}]

    for _ in range(repeat_count):
        for layout in (layout1, layout2, layout3):
            manager = StorageManager()
            disk = manager.add_disk(id=test_disk)
            for part in layout:
                disk.add_partition(id=part['id'], fs_type=part['fs_type'], size=part['size'],
                                   mount_point=part['mount_point'])

            manager.create_filesystems()

            for part in disk.partitions:
                run_cmd(args=['rm', part.block_device])
