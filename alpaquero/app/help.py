#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
from typing import TYPE_CHECKING

import os
import urwid

from subiquitycore.ui.stretchy import Stretchy
from subiquitycore.ui.buttons import ok_btn
from subiquitycore.ui.utils import button_pile

from alpaquero.app.distro import DISTRO_NAME
from alpaquero.controllers.storage import StorageController

if TYPE_CHECKING:
    from .application import ApplicationUI


class HelpMsgStretchy(Stretchy):
    MSG = """
Welcome to the {} Installer!

This program will guide you through all the steps to install {} on one of your disks.

The procedure requires a disk minimum of {:.1f} GB size and an active network connection to the Internet or a private repository with APK packages.
"""

    def __init__(self, app_ui: ApplicationUI, min_disk_size: float):
        self._app_ui = app_ui
        _ok_btn = ok_btn('Close', on_press=self._close)
        text = self.MSG.format(DISTRO_NAME, DISTRO_NAME, min_disk_size / StorageController.GB)
        text_extra = ''
        if app_ui.app.iso_mode:
            term = os.getenv('TERM', '')
            if term.startswith('linux'):
                text_extra = '''
Additional shell sessions are available on other virtual terminals. You can switch to them using Ctrl+Alt+Fn or Alt+Left/Right key combinations.
'''
            elif term.startswith('screen'):
                text_extra = '''
This program is operating within a Screen session. Type 'Ctrl+a c' to create a new window with a shell or 'Ctrl+a ?' to get a list of available key bindings.
'''
            elif term.startswith('tmux'):
                text_extra = '''
This program is operating within a tmux session. Type 'Ctrl+b c' to create a new window with a shell or 'Ctrl+b ?' to get a list of available key bindings.
'''
        super().__init__('Help', [urwid.Text(text + text_extra),
                                  urwid.Text(''),
                                  button_pile([_ok_btn])], 0, 2)

    def _close(self, sender):
        self._app_ui.body.remove_overlay(self)
