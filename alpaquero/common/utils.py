#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import enum
import subprocess
import urllib
from typing import Optional, Callable, Iterable
import logging
import os
from tempfile import TemporaryDirectory

from .events import EventReceiver, LoggingReceiver

log = logging.getLogger('common.utils')

VALID_PROXY_URL_TEMPLATE = 'http://[[user][:password]@]hostname[:port]'
MEDIA_PATH = '/media/disk/apks'
DEFAULT_CONFIG_FILE = 'setup.yaml'

class Arch(enum.Enum):
    X86_64 = "x86_64"
    AARCH64 = "aarch64"


def run_cmd(args, input: Optional[bytes] = None,
            timeout: float = None, ignore_status: bool = False,
            event_receiver: EventReceiver = LoggingReceiver()) -> subprocess.CompletedProcess:

    if event_receiver:
        event_receiver.add_log_line(f'Running command: {args}')

    try:
        res = subprocess.run(args, input=input,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             preexec_fn=os.setpgrp,
                             timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        if event_receiver:
            event_receiver.add_log_line('Command did not complete in {} seconds'.format(timeout))
        raise RuntimeError("'{}' did not complete in {} seconds".format(
            ' '.join(args), timeout
        )) from None

    stdout = res.stdout.decode().replace('\\n', '\n').replace('\\t', '\t')

    if event_receiver:
        if stdout:
            event_receiver.add_log_line(f'Command output: {stdout}')
        event_receiver.add_log_line('Command exit code: {}'.format(res.returncode))

    if (not ignore_status) and (res.returncode != 0):
        raise RuntimeError("'{}' exited with {}: {}".format(
            ' '.join(args), res.returncode, stdout
        ))

    return res


def run_cmd_live(args, ignore_status: bool = False,
                 event_receiver: EventReceiver = LoggingReceiver(),
                 event_transform: Callable = None) -> subprocess.CompletedProcess:

    event_receiver.add_log_line(f'Running command: {args}')
    with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          preexec_fn=os.setpgrp) as proc:
        for b_line in iter(proc.stdout.readline, b''):
            line = b_line.decode().strip(' \n')
            if not line:
                continue
            if event_transform:
                new_line = event_transform(line)
                if new_line:
                    event_receiver.start_event(new_line)
                    continue
            event_receiver.add_log_line(line)

        ret = proc.wait()

        if (not ignore_status) and (ret != 0):
            raise RuntimeError("'{}' exited with {}".format(' '.join(args), ret))

    return subprocess.CompletedProcess(proc.args, ret)


def write_file(path, mode: str, data):
    action = {'w': 'Wrote', 'wb': 'Wrote',
              'a': 'Appended'}.get(mode, None)
    if action is None:
        raise ValueError("Unsupported mode '{}' for file '{}'".format(
            mode, path))

    with open(path, mode) as file:
        file.write(data)

    log.debug("{} to '{}' data: '{}'".format(action, path, data))


def validate_proxy_url(url: str):
    msg = "Proxy URL '{}' does not match template '{}'".format(
        url, VALID_PROXY_URL_TEMPLATE)

    pr = urllib.parse.urlparse(url)

    if (pr.scheme != 'http') or (not pr.hostname) or \
            any((pr.path, pr.params, pr.query, pr.fragment)) or \
            url.endswith(':'):
        raise ValueError(msg)

    try:
        _ = pr.port
    except ValueError:
        raise ValueError(msg) from None


def button_width_for_label(label: str) -> int:
    # '[ ' + label + ' ]'
    return len(label) + 4


def validate_apk_repo(url: str, keys_dir: str, timeout: float):
    with TemporaryDirectory() as tmpdir:
        args = ['apk', '--root', tmpdir, '--keys', keys_dir,
                '--repository', url]
        try:
            run_cmd(args=(args + ['add', '--initdb']))
            run_cmd(args=(args + ['update']), timeout=timeout)
            res = run_cmd(args=(args + ['list', '-a']))
        except RuntimeError as exc:
            raise ValueError(str(exc)) from None

        if not res.stdout:
            raise ValueError('Repository {} contains no packages.'.format(url))


def validate_apk_repos(urls: Iterable[str], keys_dir: str, timeout: float):
    for url in urls:
        validate_apk_repo(url=url, keys_dir=keys_dir, timeout=timeout)
