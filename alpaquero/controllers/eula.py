#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
from typing import TYPE_CHECKING
import os

import alpaquero
from .controller import Controller
from alpaquero.views.eula import EULAView

if TYPE_CHECKING:
    from alpaquero.app.application import Application


class EULAController(Controller):
    def __init__(self, app: Application):
        super().__init__(app)

        dir_path = os.path.abspath(os.path.realpath(alpaquero.__file__))
        dir_path = os.path.dirname(dir_path)
        with open(os.path.join(dir_path, 'EULA'), 'r') as file:
            self._content = file.read()
        self._content = self._content.replace(" \n", " ")

    def make_ui(self):
        return EULAView(self, self._content, iso_mode=self._app.iso_mode)

    def done(self):
        self._app.next_screen()

    def cancel(self):
        if self._app.iso_mode:
            self._app.reboot()
        else:
            self._app.exit()
