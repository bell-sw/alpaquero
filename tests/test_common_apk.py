#  SPDX-FileCopyrightText: 2023 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import os

import pytest

from alpaquero.common.apk import APKManager
from .utils import StubEventReceiver


def test_invalid_root_dir(tmp_path):
    apk = APKManager(event_receiver=StubEventReceiver())
    with pytest.raises(ValueError, match=r'(?i)not a directory'):
        apk.root_dir = os.path.join(tmp_path, 'not-a-dir')


def test_invalid_keys_dir(tmp_path):
    apk = APKManager(event_receiver=StubEventReceiver())
    with pytest.raises(ValueError, match=r'(?i)not a directory'):
        apk.keys_dir = os.path.join(tmp_path, 'not-a-dir')


def test_write_read_repo_file(tmp_path):
    root_dir = os.path.join(tmp_path, 'root')
    os.makedirs(root_dir)

    apk = APKManager(event_receiver=StubEventReceiver())
    apk.root_dir = root_dir
    data = '''\
    line1
    line2
'''
    apk.write_repo_file(data=data)

    with open(os.path.join(root_dir, 'etc/apk/repositories'), 'r') as file:
        read_data = file.read()
        assert read_data == data

    assert apk.read_repo_file() == data
