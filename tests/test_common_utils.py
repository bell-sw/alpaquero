#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import os
from typing import Optional

import pytest
import pytest_httpserver

from alpaquero.common.events import EventReceiver
from alpaquero.common.utils import (
    run_cmd, run_cmd_live, write_file, button_width_for_label,
    validate_proxy_url, validate_apk_repo)
from .utils import StubEventReceiver


def test_run_cmd_timeout():
    receiver = StubEventReceiver()
    with pytest.raises(RuntimeError, match=r'(?i)did not complete'):
        run_cmd(args=['sleep', '1'], timeout=0.1, event_receiver=receiver)
    assert receiver.log_lines[1] == 'Command did not complete in 0.1 seconds'


def test_run_cmd_returncode():
    receiver = StubEventReceiver()
    with pytest.raises(RuntimeError, match=r'(?i)exited with 1'):
        run_cmd(args=['false'], event_receiver=receiver)
    assert receiver.log_lines[1] == 'Command exit code: 1'

    res = run_cmd(args=['false'], ignore_status=True)
    assert res.returncode == 1


def test_run_cmd_output():
    receiver = StubEventReceiver()
    data = 'some_data'
    res = run_cmd(args=['cat'], input=bytes(data, encoding='utf-8'), event_receiver=receiver)
    assert data == res.stdout.decode()
    assert receiver.log_lines[1] == f'Command output: {data}'
    assert res.returncode == 0


def test_run_cmd_live_event_transform():
    def _transform(line: str) -> Optional[str]:
        if line.startswith('A'):
            return 'A'
        return None

    class Receiver(EventReceiver):
        event_prefix = 'Started event: '
        data = []

        def start_event(self, msg):
            self.data.append(f'{self.event_prefix}{msg}')

        def stop_event(self):
            pass

        def add_log_line(self, msg):
            self.data.append(msg)

    recv = Receiver()
    data = r'B\nA\n  \nC\n  A'
    res = run_cmd_live(args=['echo', '-e', '-n', data], event_receiver=recv,
                       event_transform=_transform)
    # Skip the first 'Running command ...' add_log_line
    assert recv.data[1:] == ['B', f'{recv.event_prefix}A', 'C', f'{recv.event_prefix}A']
    assert res.returncode == 0


def test_run_cmd_live_output_returncode():
    with pytest.raises(RuntimeError, match=r'(?i)exited with 1'):
        run_cmd_live(args=['false'])

    res = run_cmd_live(args=['false'], ignore_status=True)
    assert res.returncode == 1


def test_write_file(tmp_path):
    file_path = os.path.join(tmp_path, 'temp_file')
    data = 'some data'
    bdata = bytes(data, encoding='utf-8')

    write_file(path=file_path, mode='w', data=data)
    with open(file_path, 'r') as file:
        assert data == file.read()

    write_file(path=file_path, mode='a', data=data)
    with open(file_path, 'r') as file:
        assert data + data == file.read()

    write_file(path=file_path, mode='wb', data=bdata)
    with open(file_path, 'rb') as file:
        assert bdata == file.read()

    with pytest.raises(ValueError, match=r'(?i)unsupported mode'):
        write_file(path=file_path, mode='invalid mode', data=data)


def test_validate_proxy_url():
    invalid_urls = ['ftp://domain.com:80',
                    'https://domain.com:80',
                    'http://domain.com:invalid_port',
                    'http://domain.com:80/path',
                    'http://domain.com/path',
                    'http://domain.com/path/',
                    'http://domain.com:port',
                    'http://domain.com?arg=val',
                    'http://',
                    'domain.com:80',
                    'domain.com',
                    ]

    for url in invalid_urls:
        with pytest.raises(ValueError, match=r'(?i)does not match template'):
            validate_proxy_url(url)


def test_button_width_for_label():
    label = 'some label'
    assert len(f'[ {label} ]') == button_width_for_label(label)


def test_validate_apk_repo_bad_url(httpserver: pytest_httpserver.HTTPServer,
                                   tmp_path_factory: pytest.TempPathFactory):
    with pytest.raises(ValueError, match=r'(?i)remote server returned error'):
        validate_apk_repo(url=httpserver.url_for('/bad_url'),
                          keys_dir=str(tmp_path_factory.mktemp('bad_url')), timeout=5)


def test_validate_apk_repo_no_packages(httpserver: pytest_httpserver.HTTPServer,
                                       tmp_path_factory: pytest.TempPathFactory):
    tmpdir = tmp_path_factory.mktemp('no_packages')
    keys_dir = tmpdir / 'keys'
    os.makedirs(keys_dir)

    # In the future the key generation may be moved into a fixture.
    privkey = keys_dir / 'apk.rsa'
    pubkey = keys_dir / 'apk.rsa.pub'
    run_cmd(args=['openssl', 'genrsa', '-out', str(privkey), '2048'])
    run_cmd(args=['openssl', 'rsa', '-in', str(privkey), '-pubout', '-out', str(pubkey)])

    os.chdir(tmpdir)
    apkindex = 'APKINDEX.tar.gz'
    run_cmd(args=['apk', 'index', '-o', apkindex])
    run_cmd(args=['abuild-sign', '-k', str(privkey), apkindex])

    arch = os.uname()[4]
    httpserver.expect_request(uri=f'/no_packages/{arch}/{apkindex}', method='GET').respond_with_data(
        response_data=open(apkindex, 'br').read(), content_type='application/octet-stream')

    with pytest.raises(ValueError, match=r'(?i)contains no packages'):
        validate_apk_repo(url=httpserver.url_for('/no_packages'), keys_dir=str(keys_dir), timeout=5)
