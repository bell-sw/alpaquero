#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import urllib
import yaml
import logging
import os
from typing import Tuple, Set
from .controller import Controller
import alpaquero
from alpaquero.app.distro import DISTRO, DISTRO_REPO_BASE_URL
from alpaquero.views.repo import RepoView
from alpaquero.common.utils import MEDIA_PATH, validate_apk_repos

log = logging.getLogger('controllers.repo')


class RepoController(Controller):
    REPO_CHECK_TIMEOUT = 30

    def __init__(self, app):
        super().__init__(app)
        self._repo_base_url = DISTRO_REPO_BASE_URL
        ver_id = self.get_os_release().get('VERSION_ID', '').split('.')
        self._release = ver_id[0] if len(ver_id) > 1 and ver_id[0] else 'stream'
        self._libc_type = 'musl' if os.path.exists(f"/lib/ld-musl-{app.arch.value}.so.1") else 'glibc'
        self._host_libc_type = self._libc_type
        self._validated_repo_pairs: Set[Tuple[str, str]] = set()

    def get_os_release(self):
        res = {}
        with open('/etc/os-release') as f:
            for line in f:
                k, v = line.rstrip().split('=')
                res[k] = v
        return res

    def get_libc_type(self) -> str:
        return self._libc_type

    def make_ui(self):
        return RepoView(self, self._repo_base_url, self._libc_type,
                        iso_mode=self._app.iso_mode)

    async def _update_url_libc(self, repo_base_url: str, libc_type: str):
        try:
            repo_pair = (repo_base_url, libc_type)
            if repo_pair not in self._validated_repo_pairs:
                task = self._app.aio_loop.run_in_executor(None, validate_apk_repos,
                                                          self.get_repos(repo_base_url, libc_type),
                                                          self.get_keys_dir(libc_type),
                                                          self.REPO_CHECK_TIMEOUT)
                await self._app.wait_with_text_dialog(task, 'Checking repositories')
                self._validated_repo_pairs.add(repo_pair)

            self._repo_base_url = repo_base_url
            self._libc_type = libc_type
            log.debug("libc: {}, base_url: '{}'".format(self._libc_type, self._repo_base_url))
            self._app.next_screen()
        except ValueError as exc:
            self._app.show_error_message(str(exc))
            self._app.aio_loop.call_soon(self._app.urwid_loop.draw_screen)

    def done(self, repo_base_url: str, libc_type: str):
        self._app.aio_loop.create_task(self._update_url_libc(repo_base_url, libc_type))

    def cancel(self):
        self._app.prev_screen()

    def get_repos(self, url, libc):
        repos = []
        for name in ['core', 'universe']:
            repos.append(urllib.parse.quote(
                f'{url}/{DISTRO}/{libc}/{self._release}/{name}',
                safe='/:'))
        return repos

    def get_keys_dir(self, libc) -> str:
        ai_path = os.path.abspath(os.path.realpath(alpaquero.__file__))
        return os.path.join(os.path.dirname(ai_path), 'keys', libc)

    def to_yaml(self):
        res = []

        if self._app.iso_mode and (self._host_libc_type == self._libc_type):
            res.append(MEDIA_PATH)
        res.extend(self.get_repos(self._repo_base_url, self._libc_type))

        yaml_data = yaml.dump({"repositories": {
            'keys': self.get_keys_dir(self._libc_type),
            'urls': res,
        }})

        log.debug(f"export to yaml: {yaml_data}")
        return yaml_data
