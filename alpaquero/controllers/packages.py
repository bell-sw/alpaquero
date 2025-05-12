#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import yaml
import glob
import logging
from .controller import Controller
from alpaquero.app.distro import DISTRO, DISTRO_JDK8, DISTRO_JDK11, DISTRO_JDK17, \
    DISTRO_JDK21, DISTRO_NIK23_17, DISTRO_NIK23_21, DISTRO_NIK24_22
from alpaquero.views.packages import PackagesView

log = logging.getLogger('controllers.packages')


class PackagesController(Controller):
    def __init__(self, app):
        super().__init__(app)

        #Determine if the ISO is of type "virt" or not
        is_virt = False
        try:
            #.alpaquita-release file is in the format of ${image_name}-${RELEASE} ${build_date}
            #and ${image_name} is formatted like image_name="alpaquita-${PROFILE}"
            #.alpaquita-release should be smth like: alpaquita-virt-240901 240901 if virt type
            with open("/media/disk/.alpaquita-release", "r") as f:
                is_virt = '-virt-' in f.readline()
        except FileNotFoundError:
            pass
        self._data = {'kernel': {'extramods': not is_virt},
                      'other': {'ssh_server': True}}

        log.debug(f'init: {self._data}')

    def make_ui(self):
        self._is_musl = self._app.controller('RepoController').get_libc_type() == 'musl'
        return PackagesView(self, self._data, self._is_musl)

    def done(self, data: dict):
        log.debug(f'done: {data}')

        self._data = data
        self._app.next_screen()

    def cancel(self):
        self._app.prev_screen()

    def _is_group_item(self, group: str, item: str):
        return self._data.get(group).get(item)

    def _add_pkg(self, pkgs, group, name, pkg_name):
        if (group not in self._data) or (name not in self._data.get(group)):
            return
        if self._is_group_item(group=group, item=name):
            pkgs.append(pkg_name)

    def to_yaml(self):
        epkgs = []
        enable_services = []

        self._add_pkg(epkgs, 'kernel', 'extramods', 'linux-lts-extra-modules')

        self._add_pkg(epkgs, 'jdk', 'jdk_8', DISTRO_JDK8.package)
        self._add_pkg(epkgs, 'jdk', 'jdk_11', DISTRO_JDK11.package)
        self._add_pkg(epkgs, 'jdk', 'jdk_17', DISTRO_JDK17.package)
        self._add_pkg(epkgs, 'jdk', 'jdk_21', DISTRO_JDK21.package)
        self._add_pkg(epkgs, 'jdk', 'nik_23_17', DISTRO_NIK23_17.package)
        self._add_pkg(epkgs, 'jdk', 'nik_23_21', DISTRO_NIK23_21.package)
        self._add_pkg(epkgs, 'jdk', 'nik_24_22', DISTRO_NIK24_22.package)

        self._add_pkg(epkgs, 'libc', 'perf', 'musl-perf')

        self._add_pkg(epkgs, 'other', 'ssh_server', 'openssh')
        self._add_pkg(epkgs, 'other', 'ssh_server', 'openssh-server')
        if self._is_group_item(group='other', item='ssh_server'):
            enable_services.append('sshd')

        self._add_pkg(epkgs, 'other', 'coreutils', 'coreutils')

        data = {'extra_packages': epkgs}
        if enable_services:
            data['services'] = {'enabled': enable_services}

        return yaml.dump(data)
