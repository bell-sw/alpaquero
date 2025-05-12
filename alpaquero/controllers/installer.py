#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
import asyncio
import yaml
import logging
import abc
import os
import shutil
import stat
from typing import TYPE_CHECKING

from subiquitycore.async_helpers import run_in_thread
from alpaquero.views.installer import InstallerView
from alpaquero.installers.storage import StorageInstaller
from alpaquero.installers.repo import RepoInstaller
from alpaquero.installers.proxy import ProxyInstaller
from alpaquero.installers.packages import PackagesInstaller
from alpaquero.installers.services import ServicesInstaller
from alpaquero.installers.swapfile import SwapfileInstaller
from alpaquero.installers.timezone import TimezoneInstaller
from alpaquero.installers.users import UsersInstaller
from alpaquero.installers.network import NetworkInstaller
from alpaquero.installers.kernel import KernelInstaller
from alpaquero.installers.secureboot import SecureBootInstaller
from alpaquero.installers.bootloader import BootloaderInstaller
from alpaquero.installers.post_scripts import PostScriptsInstaller
from alpaquero.installers.installer import InstallerException
from alpaquero.common.apk import APKManager
from alpaquero.common.events import EventReceiver
from alpaquero.common.utils import DEFAULT_CONFIG_FILE, Arch
from .controller import Controller

if TYPE_CHECKING:
    from alpaquero.app.application import Application

log = logging.getLogger('controllers.installer')


def err_msg_with_debug_log_file(err_msg: str, app: Application):
    if app.debug_log_file:
        return f"{err_msg}\nAdditional debug information is available in '{app.debug_log_file}'."
    else:
        return err_msg


class BaseInstallerController(Controller, EventReceiver):
    TARGET_ROOT = '/mnt/target_root'

    def __init__(self, app: Application, create_config, config_file):
        super().__init__(app)
        self._config_file = config_file
        self._create_config = create_config

        os.environ['TARGET_ROOT'] = self.TARGET_ROOT

    def _run(self):
        try:
            if self._create_config:
                self.create_config()
            self._install_config()
        except Exception as err:
            raise InstallerException(f'An error occurred: {err}')

    def _copy_yaml_config(self):
        copied_config_rel = os.path.join('/root', os.path.basename(DEFAULT_CONFIG_FILE))
        self.start_event((f"Saving the config file for this installation to "
                          f"'{copied_config_rel}' on the new system."))
        copied_config_abs = os.path.join(self.TARGET_ROOT, copied_config_rel.lstrip('/'))
        shutil.copy(self._config_file, copied_config_abs)
        os.chown(copied_config_abs, 0, 0)
        os.chmod(copied_config_abs, stat.S_IRUSR | stat.S_IWUSR)

    def _install_config(self):
        self.start_event('Processing configuration')
        self.add_log_line(f'Parsing config {self._config_file} file')

        with open(self._config_file) as f:
            config_str = f.read()

        if not config_str:
            raise InstallerException(f'Config is empty')

        try:
            config = yaml.safe_load(config_str)
        except yaml.YAMLError as err:
            raise InstallerException(f"Failed to parse '{self._config_file}' file: {err}")

        self.add_log_line(f'Creating a temporary root {self.TARGET_ROOT}')
        os.makedirs(self.TARGET_ROOT, exist_ok=True)

        storage_installer = StorageInstaller(target_root=self.TARGET_ROOT,
                                             config=config, event_receiver=self)
        arch = Arch(os.uname().machine)
        efi_mount = storage_installer.efi_mount_point
        apk = APKManager(event_receiver=self)
        apk.root_dir = self.TARGET_ROOT
        pkgs_installer = PackagesInstaller(target_root=self.TARGET_ROOT,
                                           config=config, event_receiver=self, apk=apk)

        installers = [
            storage_installer,
            RepoInstaller(target_root=self.TARGET_ROOT, config=config, event_receiver=self,
                          apk=apk),
            ProxyInstaller(target_root=self.TARGET_ROOT, config=config, event_receiver=self),
            pkgs_installer,
            ServicesInstaller(target_root=self.TARGET_ROOT, config=config, event_receiver=self),
            SwapfileInstaller(target_root=self.TARGET_ROOT, config=config, event_receiver=self),
            TimezoneInstaller(target_root=self.TARGET_ROOT, config=config, event_receiver=self),
            UsersInstaller(target_root=self.TARGET_ROOT, config=config, event_receiver=self),
            NetworkInstaller(target_root=self.TARGET_ROOT, config=config, event_receiver=self),
            KernelInstaller(target_root=self.TARGET_ROOT, config=config, event_receiver=self),
            BootloaderInstaller(target_root=self.TARGET_ROOT, config=config, event_receiver=self,
                                arch=arch, efi_mount=efi_mount),
            SecureBootInstaller(target_root=self.TARGET_ROOT, config=config, event_receiver=self,
                                apk=apk),
            PostScriptsInstaller(target_root=self.TARGET_ROOT, config=config, event_receiver=self),
        ]

        for i in installers:
            pkgs_installer.add_package(*i.packages)

        for i in installers:
            i.apply()

        for i in installers:
            i.post_apply()

        if self._app.copy_config:
            self._copy_yaml_config()

        for i in reversed(installers):
            i.cleanup()

        self.add_log_line(f'Removing {self.TARGET_ROOT}')
        os.rmdir(self.TARGET_ROOT)

        self.start_event('\nInstallation complete!')


class ConsoleInstallerController(BaseInstallerController):
    def __init__(self, app: Application, config_file):
        super().__init__(app, False, config_file)

    def run(self):
        try:
            self._run()
        except Exception as err:
            self.add_log_line(f'{err}')
            print(err_msg_with_debug_log_file(f'{err}', app=self._app))
            return 1
        return 0

    def start_event(self, msg):
        self.add_log_line(msg)
        print(msg)

    def stop_event(self):
        pass

    def add_log_line(self, msg):
        # No need to litter the stdout. If you need details, just enable debugging.
        log.debug(msg)


class InstallerController(BaseInstallerController):
    def __init__(self, app: Application, create_config=True, config_file=DEFAULT_CONFIG_FILE):
        super().__init__(app, create_config, config_file)
        self._view = InstallerView(self, iso_mode=self._app.iso_mode)
        self._eloop = asyncio.get_event_loop()

    def create_config(self):
        self.add_log_line(f'Creating config {self._config_file} file')
        with open(self._config_file, 'w') as f:
            for c in self._app.controllers():
                yaml_str = c.to_yaml()
                if yaml_str:
                    f.write(yaml_str + '\n')

    async def _start(self):
        try:
            await run_in_thread(self._run)
        except Exception as err:
            self._add_log_line(f'{err}')
            self._event_start_no_logs(err_msg_with_debug_log_file(f'{err}', app=self._app))
            self._event_finish()
            self._view.done()
            return

        self._event_finish()
        self._view.done()

    def add_log_line(self, msg):
        self._eloop.call_soon_threadsafe(self._add_log_line, msg)

    def start_event(self, msg):
        self._eloop.call_soon_threadsafe(self._event_start, msg)

    def stop_event(self):
        self._eloop.call_soon_threadsafe(self._event_finish)

    def _event_start(self, msg):
        self._add_log_line(msg)
        self._event_start_no_logs(msg)

    def _event_start_no_logs(self, msg):
        self._event_finish()
        self._view.event_start('', '', msg)

    def _event_finish(self):
        self._view.event_finish('')

    def _add_log_line(self, msg):
        log.debug(msg)
        self._view.add_log_line(msg)

    def click_cancel(self):
        self._app.exit()

    def click_reboot(self):
        self._app.reboot()

    def click_poweroff(self):
        self._app.poweroff()

    def make_ui(self):
        self._event_start('Starting installation')
        self._app.aio_loop.create_task(self._start())
        return self._view
