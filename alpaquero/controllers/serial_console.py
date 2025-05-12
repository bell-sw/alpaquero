#  SPDX-FileCopyrightText: 2024 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import logging
import os
import sys

import yaml

from alpaquero.views.serial_console import SerialConsoleView
from alpaquero.common.utils import run_cmd
from .controller import Controller

log = logging.getLogger('controllers.serial_console')


def get_serial_ttys() -> list[str]:
    ttys = []

    for name in os.listdir("/sys/class/tty"):
        path = os.path.join("/sys/class/tty", name)
        if not os.path.isdir(path):
            continue

        if os.path.isfile(os.path.join(path, "active")):
            continue

        if not os.path.exists(os.path.join(path, "device")):
            continue

        res = run_cmd(args=["stty", "-F", f"/dev/{name}", "-g"],
                      ignore_status=True)
        if res.returncode == 0:
            ttys.append(name)
        
    return ttys


def get_active_tty() -> str:
    return os.ttyname(sys.stdin.fileno()).removeprefix("/dev/")


class SerialConsoleController(Controller):
    def __init__(self, app):
        super().__init__(app)

        ttys = get_serial_ttys()
        active_tty = get_active_tty()

        self._active_tty = active_tty if active_tty in ttys else ""
        self._tty_state = {}
        for tty in ttys:
            # If we were able to detect the active serial tty,
            # enable only it by default. Otherwise, enable all ttys
            value = True
            if self.active_tty:
                value = tty == self.active_tty
            self._tty_state[tty] = value

        self._show_ui = bool(self._tty_state)
        if not self._tty_state:
            log.debug("No serial ttys detected")


    @property
    def tty_state(self) -> dict[str, bool]:
        return dict(self._tty_state)

    @property
    def active_tty(self) -> str | None:
        return self._active_tty

    def make_ui(self):
        return SerialConsoleView(self) if self._show_ui else None

    def done(self, tty_state: dict[str, bool]):
        for tty in self._tty_state.keys():
            old_val = self._tty_state[tty]
            new_val = tty_state.get(tty, False)
            if old_val != new_val:
                log.debug(f"Serial tty {tty}, old value '{old_val}', new value '{new_val}'")
                self._tty_state[tty] = new_val

        log.debug(f"Serial tty state: {self._tty_state}")

        self._app.next_screen()

    def cancel(self):
        self._app.prev_screen()

    def to_yaml(self) -> str:
        ttys = [tty for tty, value in self._tty_state.items() if value]
        if not ttys:
            return ''

        scripts = [] 
        for tty in sorted(ttys):
            scripts.append({
                "interpreter": "/bin/sh",
                "chroot": True,
                "script": f"sed -i '/^{tty}:/d' /etc/inittab"
            })
            scripts.append({
                "interpreter": "/bin/sh",
                "chroot": True,
                "script": f"echo '{tty}::respawn:/usr/sbin/getty -L {tty} 115200 vt220' >> /etc/inittab"
            })

        yaml_data = yaml.dump({"post_scripts": scripts})
        log.debug(f"export to yaml: {yaml_data}")
        return yaml_data