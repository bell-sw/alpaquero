#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import re
import time
import logging

from alpaquero.common.utils import run_cmd

log = logging.getLogger('nmanager.utils')


def wait_iface_gets_ip(iface_name: str, ip_ver: int, timeout: float):
    if ip_ver == 4:
        inet_pattern = r'^\s*inet\s+'
    elif ip_ver == 6:
        inet_pattern = r'^\s*inet6\s+'
    else:
        raise ValueError(f'IP version is {ip_ver}, but only IPv4 and IPv6 are supported')

    sleep_interval = 1
    avail = timeout
    while avail > 0:
        args = ['ip', '-{}'.format(ip_ver), 'addr', 'show',
                'dev', iface_name, 'scope', 'global']
        res = run_cmd(args)
        stdout = res.stdout.decode('utf-8')
        for line in stdout.split('\n'):
            if re.match(inet_pattern, line):
                return

        time.sleep(sleep_interval)
        avail -= sleep_interval

    if avail <= 0:
        raise RuntimeError('Interface {} did not receive an IPv{} address in {} seconds'.format(
            iface_name, ip_ver, timeout
        ))


def get_active_iface_names() -> set[str]:
    ifstate_path = '/run/ifstate'
    res = set()
    try:
        with open(ifstate_path, 'r') as file:
            for line in file.readlines():
                res.add(line.split('=')[0].strip())
    except FileNotFoundError:
        log.debug('{} does not exist'.format(ifstate_path))
    return res
