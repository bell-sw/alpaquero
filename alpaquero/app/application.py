#  SPDX-FileCopyrightText: 2020 Canonical, Ltd
#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
import asyncio
import urwid
import sys
import getopt
import os
import atexit
import logging
import signal
import argparse
from typing import TYPE_CHECKING, Optional

from subiquitycore.ui.utils import Color, LoadingDialog, Padding
from subiquitycore.ui.buttons import header_btn

from alpaquero.app.distro import DISTRO_NAME
from alpaquero.common.utils import run_cmd, Arch
from alpaquero.controllers.eula import EULAController
from alpaquero.controllers.timezone import TimezoneController
from alpaquero.controllers.proxy import ProxyController
from alpaquero.controllers.repo import RepoController
from alpaquero.controllers.user import UserController
from alpaquero.controllers.network import NetworkController
from alpaquero.controllers.storage import StorageController
from alpaquero.controllers.serial_console import SerialConsoleController
from alpaquero.controllers.secureboot import SecureBootController
from alpaquero.controllers.packages import PackagesController
from alpaquero.controllers.installer import (
    InstallerController,
    ConsoleInstallerController,
)
from .error import ErrorMsgStretchy
from .help import HelpMsgStretchy

if TYPE_CHECKING:
    from subiquitycore.view import BaseView

# From Ubuntu
# When waiting for something of unknown duration, block the UI for at
# most this long before showing an indication of progress.
MAX_BLOCK_TIME = 0.1
# If an indication of progress is shown, show it for at least this
# long to avoid excessive flicker in the UI.
MIN_SHOW_PROGRESS_TIME = 1.0

DEFAULT_LOG_FILE = "installer.log"


class ApplicationUI(urwid.WidgetWrap):
    block_input = False

    def __init__(self, app: Application):
        self._app = app
        self._help_msg = HelpMsgStretchy(self,
                                         min_disk_size=app.min_disk_size)
        self._shown_help_msg = None

        self._title = urwid.Text('Title', align='left')
        help_btn = header_btn('Help (F1)', on_press=self._show_help)
        cols = urwid.Columns([('pack', self._title),
                              urwid.Padding(help_btn, align='right', width=13)])
        pile_items = [
            (1, Color.frame_header_fringe(urwid.SolidFill('\N{upper half block}'))),
            ('pack', Color.frame_header(Padding.center_79(cols, min_width=76))),
            (1, Color.frame_header_fringe(urwid.SolidFill('\N{lower half block}'))),
            urwid.Text('Body')
        ]
        self._pile = urwid.Pile(pile_items)
        self._body_pos = len(pile_items) - 1
        self._pile.focus_position = self._body_pos

        super().__init__(Color.body(self._pile))

    def set_title(self, title):
        prefix = f'{DISTRO_NAME} Installation'
        if title:
            text = '{} - {}'.format(prefix, title)
        else:
            text = prefix
        self._title.set_text(text)

    def set_body(self, body: BaseView):
        self._pile.contents[self._body_pos] = (body, self._pile.contents[self._body_pos][1])

    @property
    def body(self) -> BaseView:
        return self._pile.contents[self._body_pos][0]

    @property
    def app(self) -> Application:
        return self._app

    def _show_help(self, sender=None):
        if self._shown_help_msg is None:
            def on_close():
                self._shown_help_msg = None
            urwid.connect_signal(self._help_msg, 'closed', on_close)
            self._shown_help_msg = self._help_msg
            self.body.show_stretchy_overlay(self._shown_help_msg)
            self._pile.focus_position = self._body_pos

    def keypress(self, size, key: str):
        if not self.block_input:
            if key == 'f1':
                self._show_help()
            else:
                return super().keypress(size, key)


class Application:
    make_ui = ApplicationUI

    def __init__(self, palette=()):

        self._no_ui = False
        self._iso_mode = False
        self._debug_log_file = None
        self._copy_config = True
        self._shim_unsigned = False
        self._arch = Arch(os.uname().machine)
        # It is the default value in urwid.
        # Setting it explicitly in case urwid changes it.
        self._colors = 16

        parser = argparse.ArgumentParser(prog="python -m alpaquero",
                                         description=f"{DISTRO_NAME} Installer")
        parser.add_argument("-f", "--config-file",
                            help="get setup configuration from yaml file")
        parser.add_argument("-n", "--no-ui", action="store_true",
                            help="run the installation without a text-based UI. Requires config-file option")
        debug_group = parser.add_mutually_exclusive_group()
        debug_group.add_argument("-d", "--debug", action="store_true",
                                 help=f"write debug logs to '{DEFAULT_LOG_FILE}'")
        debug_group.add_argument("--debug-log",
                                 help="write debug logs to a file")
        parser.add_argument("-i", "--iso-mode", action="store_true",
                            help="run the installer in the ISO mode (no exit feature in the UI)")
        parser.add_argument("--no-config-copy", action="store_true",
                            help="do not copy config file to the installed system")
        parser.add_argument("--shim-unsigned", action="store_true",
                            help="display menu with shim installation option")
        parser.add_argument("--no-colors", action="store_true",
                            help="do not use colors")

        args = parser.parse_args()

        self._config_file = args.config_file if args.config_file else ''
        self._no_ui = args.no_ui
        if args.debug:
            self._debug_log_file = os.path.abspath(DEFAULT_LOG_FILE)
        elif args.debug_log:
            self._debug_log_file = os.path.abspath(args.debug_log)
        self._iso_mode = args.iso_mode
        self._copy_config = not args.no_config_copy
        self._shim_unsigned = args.shim_unsigned
        if args.no_colors:
            self._colors = 1

        if self._no_ui and not self._config_file:
            parser.error("--no-ui must be set with --config-file")

        if self._debug_log_file:
            logging.basicConfig(filename=self._debug_log_file, filemode='w',
                                format=f"%(asctime)s:{logging.BASIC_FORMAT}",
                                level=logging.DEBUG)

        if self._iso_mode:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGQUIT, signal.SIG_IGN)

        self._controllers = []

        if self._config_file:
            if self._no_ui:
                self._console_installer = ConsoleInstallerController(self, self._config_file)
                return
            self._controllers.append(InstallerController(self, False, self._config_file))
        else:
            self._controllers.extend([
                EULAController(self),
                NetworkController(self),
                ProxyController(self),
                RepoController(self),
                PackagesController(self),
                TimezoneController(self),
                UserController(self),
                SerialConsoleController(self),
                StorageController(self),
                SecureBootController(self),
                InstallerController(self)
            ])

        self._type_to_controller = {}
        for c in self._controllers:
            self._type_to_controller[type(c).__name__] = c

        self._ctrl_idx = 0

        self.ui = self.make_ui(self)
        self._palette = palette

        screen = urwid.raw_display.Screen()
        screen.register_palette(self._palette)
        screen.set_terminal_properties(colors=self._colors)

        atexit.register(self.cleanup)
        self.aio_loop = asyncio.get_event_loop()
        self.urwid_loop = urwid.MainLoop(widget=self.ui, screen=screen,
                                         handle_mouse=False, pop_ups=True,
                                         event_loop=urwid.AsyncioEventLoop(loop=self.aio_loop))

    @property
    def debug_log_file(self) -> Optional[str]:
        return self._debug_log_file

    @property
    def iso_mode(self) -> bool:
        return self._iso_mode

    @property
    def copy_config(self) -> bool:
        return self._copy_config

    @property
    def min_disk_size(self) -> float:
        size = StorageController.ROOT_MIN_SIZE + StorageController.BOOT_SIZE
        if self.is_efi():
            size += StorageController.BOOT_EFI_SIZE
        else:
            size += StorageController.BIOS_BOOT_SIZE
        return size

    @property
    def arch(self) -> Arch:
        return self._arch

    def is_efi(self) -> bool:
        return os.path.exists('/sys/firmware/efi')

    def is_shim_unsigned(self) -> bool:
        return self._shim_unsigned

    def controllers(self):
        return self._controllers

    def controller(self, type_name):
        return self._type_to_controller.get(type_name)

    def run(self):
        if self._no_ui:
            sys.exit(self._console_installer.run())

        if not self._display_screen():
            self.next_screen()
        self.urwid_loop.run()

    def _move_screen(self, increment):
        prev_idx = self._ctrl_idx

        if increment > 0:
            self._ctrl_idx = min(self._ctrl_idx + 1, len(self._controllers) - 1)
        else:
            self._ctrl_idx = max(self._ctrl_idx - 1, 0)

        if prev_idx == self._ctrl_idx:
            return

        if not self._display_screen():
            self._move_screen(increment)

    def next_screen(self):
        self._move_screen(1)

    def prev_screen(self):
        self._move_screen(-1)

    def _display_screen(self):
        view = self._controllers[self._ctrl_idx].make_ui()
        if view is None:
            return False

        self.ui.set_title(view.title)
        self.ui.set_body(view)
        return True

    def show_error_message(self, msg: str):
        self.ui.body.show_stretchy_overlay(ErrorMsgStretchy(self, msg))

    # From Ubuntu TuiApplication
    async def _wait_with_indication(self, awaitable, show, hide=None):
        """Wait for something but tell the user if it takes a while.

        When waiting for something that can take an unknown length of
        time, we want to tell the user if it takes more than a moment
        (defined as MAX_BLOCK_TIME) but make sure that we display any
        indication for long enough that the UI is not flickering
        incomprehensibly (MIN_SHOW_PROGRESS_TIME).
        """
        min_show_task = None

        def _show():
            self.ui.block_input = False
            nonlocal min_show_task
            min_show_task = self.aio_loop.create_task(
                asyncio.sleep(MIN_SHOW_PROGRESS_TIME))
            show()

        self.ui.block_input = True
        show_handle = self.aio_loop.call_later(MAX_BLOCK_TIME, _show)
        try:
            result = await awaitable
        finally:
            if min_show_task:
                await min_show_task
                if hide is not None:
                    hide()
            else:
                self.ui.block_input = False
                show_handle.cancel()

        return result

    # From Ubuntu TuiApplication
    async def wait_with_text_dialog(self, awaitable, message,
                                    *, can_cancel=False):
        ld = None

        task_to_cancel = None
        if can_cancel:
            if not isinstance(awaitable, asyncio.Task):
                orig = awaitable

                async def w():
                    return await orig

                awaitable = task_to_cancel = self.aio_loop.create_task(w())
            else:
                task_to_cancel = None

        def show_load():
            nonlocal ld
            ld = LoadingDialog(parent=self.ui.body, aio_loop=self.aio_loop, urwid_loop=self.urwid_loop,
                               msg=message, task_to_cancel=task_to_cancel)
            self.ui.body.show_overlay(ld, width=ld.width)

        def hide_load():
            ld.close()

        return await self._wait_with_indication(
            awaitable, show_load, hide_load)

    @staticmethod
    def cleanup():
        os.system('clear')

    def exit(self):
        self.aio_loop.stop()

    @staticmethod
    def reboot():
        run_cmd(args=['reboot'])

    @staticmethod
    def poweroff():
        run_cmd(args=['poweroff'])
