#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import os
import logging
import urllib

from .installer import Installer
from alpaquero.common.utils import MEDIA_PATH, write_file
from alpaquero.common.apk import APKManager
from .utils import read_key_or_fail, read_list

log = logging.getLogger('installer.repo')

#
# repositories:
#   keys: /dir/with/keys # optional
#   urls: [ url1, url2, .. ]
#


def validate_repo_url(url: str):
    msg = "'{}' is an invalid repository url".format(url)

    url = url.strip()
    if not url:
        raise ValueError(msg)

    pr = urllib.parse.urlparse(url)
    if pr.scheme:
        if (pr.scheme not in ('http', 'https')) or (not pr.hostname):
            raise ValueError(msg)


class RepoInstaller(Installer):
    def __init__(self, target_root: str, config: dict, event_receiver, apk: APKManager):
        yaml_tag = 'repositories'
        super().__init__(name=yaml_tag, target_root=target_root,
                         event_receiver=event_receiver,
                         data_type=dict, config=config)
        self._apk = apk
        self._repo_file = ''

        self._urls = read_list(self._data, 'urls', item_type=str,
                               error_label=f'{yaml_tag}/urls')
        if not self._urls:
            raise ValueError(f"'{yaml_tag}/urls' is empty")
        for url in self._urls:
            validate_repo_url(url)

        val = read_key_or_fail(self._data, 'keys', value_type=str,
                               error_label=f'{yaml_tag}/keys')
        if val:
            self._apk.keys_dir = val

    def apply(self):
        self._event_receiver.start_event('Saving repositories')
        self._event_receiver.add_log_line(f'{self._urls}')
        self._apk.write_repo_file(data=''.join(map(lambda r: r + '\n',
                                                   self._urls)))

    def cleanup(self):
        # The repo file may have been updated outside the APKManager. For example,
        # with post install scripts. So we work with the existing file content
        self._event_receiver.add_log_line(f"Commenting '{MEDIA_PATH}' in the repo file")
        lines = []
        for r in self._apk.read_repo_file().splitlines():
            if r == MEDIA_PATH:
                r = '#' + r
            lines.append(r + '\n')
        self._apk.write_repo_file(data=''.join(lines))
