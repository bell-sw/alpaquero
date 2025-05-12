#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import logging

import yaml
from .controller import Controller
from alpaquero.views.secureboot import SecureBootView

log = logging.getLogger('controllers.secureboot')


class SecureBootController(Controller):
    def __init__(self, app):
        super().__init__(app)

        self._install_shim = not app.is_shim_unsigned()
        self._show_ui = app.is_shim_unsigned() and app.is_efi()

    def make_ui(self):
        return SecureBootView(self, self._install_shim) if self._show_ui else None

    def done(self, install_shim):
        self._install_shim = install_shim
        log.debug('Install shim: {}'.format(self._install_shim))
        self._app.next_screen()

    def cancel(self):
        self._app.prev_screen()

    def to_yaml(self):
        yaml_data = yaml.dump({'install_shim_bootloader': self._install_shim})
        log.debug('export to yaml: {}'.format(yaml_data))
        return yaml_data
