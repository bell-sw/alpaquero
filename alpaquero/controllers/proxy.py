#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import logging
import os

import yaml

from alpaquero.views.proxy import ProxyView
from .controller import Controller

log = logging.getLogger('controllers.proxy')


class ProxyController(Controller):
    ENV_VARS = ('http_proxy', 'https_proxy')

    def __init__(self, app):
        super().__init__(app)
        self.proxy = ''

    def make_ui(self):
        return ProxyView(self, self.proxy)

    def done(self, proxy: str):
        self.proxy = proxy
        # If other controllers try to access the network,
        # they should pick up the proxy configuration
        for v in self.ENV_VARS:
            if self.proxy:
                os.environ[v] = self.proxy
            elif v in os.environ:
                del os.environ[v]
        log.debug("Proxy: '{}'".format(self.proxy))
        self._app.next_screen()

    def cancel(self):
        self._app.prev_screen()

    def to_yaml(self) -> str:
        if not self.proxy:
            return ''

        yaml_data = yaml.dump({'proxy': self.proxy})
        log.debug(f"export to yaml: {yaml_data}")
        return yaml_data
