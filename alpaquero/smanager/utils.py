#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import os
import time

from alpaquero.common.utils import run_cmd


def get_block_device_size(device_path: str) -> int:
    res = run_cmd(['blockdev', '--getsize64', device_path])
    return int(res.stdout.decode())


def get_fs_uuid(device_path: str) -> str:
    res = run_cmd(args=['blkid', '-c', '/dev/null', '-o', 'value',
                        '--match-tag', 'UUID', device_path])
    uuid = res.stdout.decode().strip()
    if not uuid:
        raise RuntimeError('Unable to determine a file system UUID of {}'.format(device_path))
    return uuid


def wait_path_created(path: str, timeout=10.0):
    spent_time = 0.0
    sleep_interval = 0.1
    created = False

    while spent_time < timeout:
        if os.path.exists(path):
            created = True
            break

        time.sleep(sleep_interval)
        spent_time += sleep_interval

    if not created:
        raise RuntimeError('{}: not created in {} seconds'.format(
            path, timeout))
