#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
from typing import TYPE_CHECKING

import urwid

from subiquitycore.view import BaseView
from subiquitycore.ui.buttons import cancel_btn, done_btn
from subiquitycore.ui.container import ListBox
from subiquitycore.ui.utils import screen, Padding

from alpaquero.app.distro import DISTRO_NAME

if TYPE_CHECKING:
    from alpaquero.controllers.eula import EULAController


class EULAView(BaseView):
    title = 'End User License Agreement'
    excerpt = ('info_minor', (
        f'To install and use {DISTRO_NAME} you must read and accept '
        'the terms of the End User License Agreement (EULA).'))

    def __init__(self, controller: EULAController, content: str,
                 iso_mode: bool):
        self._controller = controller

        proceed_btn = done_btn('Accept and proceed', on_press=self.done)
        if iso_mode:
            exit_label = 'Reboot'
        else:
            exit_label = 'Exit'
        exit_btn = cancel_btn(exit_label, on_press=self.cancel)

        super().__init__(screen(urwid.LineBox(ListBox([
                                Padding.pull_1(Padding.push_1(urwid.Text(content)))])),
                                excerpt=self.excerpt,
                                buttons=[proceed_btn, exit_btn], focus_buttons=False))

    def done(self, sender):
        self._controller.done()

    def cancel(self, sender=None):
        self._controller.cancel()
