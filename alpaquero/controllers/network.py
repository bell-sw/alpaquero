#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
from typing import Optional, TYPE_CHECKING
import logging

import attrs
import yaml

from alpaquero.views.network import NetworkView
from alpaquero.nmanager.manager import NetworkManager
from alpaquero.nmanager.interface import InterfaceInfo
from alpaquero.nmanager.ip_config import IPConfig4, IPConfig6
from alpaquero.nmanager.wifi_config import WIFIConfig
from .controller import Controller

if TYPE_CHECKING:
    from alpaquero.app.application import Application

log = logging.getLogger('controllers.network')


class NetworkController(Controller):
    def __init__(self, app: Application):
        super().__init__(app)

        self._nmanager = NetworkManager()
        self._nmanager.add_host_ifaces()

        self._iface_name = self._nmanager.get_selected_iface()
        self._hostname = 'localhost'

        self._ip_config = {
            4: IPConfig4(method='dhcp'),
            6: IPConfig6(method='disabled')
        }
        if self._iface_name:
            self._ip_config[4] = self._nmanager.get_ipv4_config()
            self._ip_config[6] = self._nmanager.get_ipv6_config()

        self._wifi_config: Optional[WIFIConfig] = None

    def make_ui(self):
        return NetworkView(self)

    async def _apply_configuration(self):
        try:
            apply_task = self._app.aio_loop.run_in_executor(None,
                                                            self._nmanager.apply)
            await self._app.wait_with_text_dialog(apply_task, 'Applying configuration')
            self._app.next_screen()
        except RuntimeError as exc:
            self._app.show_error_message(str(exc))
            self._app.aio_loop.call_soon(self._app.urwid_loop.draw_screen)

    def done(self):
        self._nmanager.select_iface(self._iface_name)
        self._nmanager.set_ipv4_config(self._ip_config[4])
        self._nmanager.set_ipv6_config(self._ip_config[6])

        iface_info = self.get_iface_info(self._iface_name)
        if iface_info.type == 'wifi':
            if not self._wifi_config:
                self._app.show_error_message('Wireless network is not configured.')
                return
            self._nmanager.set_wifi_config(self._wifi_config)

        if self._nmanager.apply_required:
            self._app.aio_loop.create_task(self._apply_configuration())
        else:
            self._app.next_screen()

        log.debug('Hostname: {}'.format(self.get_hostname()))
        log.debug('Interface: {}'.format(iface_info))
        log.debug('IPv4: {}'.format(self.get_ip_config(4)))
        log.debug('IPv6: {}'.format(self.get_ip_config(6)))
        if iface_info.type == 'wifi':
            log.debug('WIFI config: {}'.format(self.get_wifi_config()))

    def cancel(self):
        self._app.prev_screen()

    def get_hostname(self) -> str:
        return self._hostname

    def set_hostname(self, hostname: str):
        self._hostname = hostname

    def select_iface(self, iface_name: str):
        self._iface_name = iface_name

    def get_selected_iface(self) -> Optional[str]:
        return self._iface_name

    def get_available_ifaces(self) -> set[str]:
        return self._nmanager.get_available_ifaces()

    def get_bond_candidates(self) -> set[str]:
        return self._nmanager.get_bond_candidates()

    def get_iface_info(self, iface_name: str) -> InterfaceInfo:
        return self._nmanager.get_iface_info(iface_name)

    def add_vlan_iface(self, base_iface_name: str, vlan_id: int):
        try:
            new_iface = self._nmanager.add_vlan_iface(base_iface_name, vlan_id)
            self._app.ui.body.update_interfaces_list(iface_to_select=new_iface)
            self._app.ui.body.remove_overlay()
        except ValueError as exc:
            self._app.show_error_message(str(exc))

    def add_bond_iface(self, name: str, members: list[str],
                       mode: str, hash_policy: Optional[str]):
        try:
            new_iface = self._nmanager.add_bond_iface(name=name, members=members,
                                                      mode=mode, hash_policy=hash_policy)
            self._app.ui.body.update_interfaces_list(iface_to_select=new_iface)
            self._app.ui.body.remove_overlay()
        except ValueError as exc:
            self._app.show_error_message(str(exc))

    def del_iface(self, iface_name: str):
        try:
            self._nmanager.del_iface(iface_name)
            self._app.ui.body.update_interfaces_list()
        except ValueError as exc:
            self._app.show_error_message(str(exc))

    def set_ip_config(self, ip_ver: int, data: dict[str, str]):
        try:
            if ip_ver not in (4, 6):
                raise ValueError(f'Unknown IP version {ip_ver}')

            if 'name_servers' in data:
                data['name_servers'] = data['name_servers'].split(',')  # type: ignore
            if 'search_domains' in data:
                data['search_domains'] = data['search_domains'].split(',')  # type: ignore

            if ip_ver == 4:
                cfg = IPConfig4(**data)
            else:
                cfg = IPConfig6(**data)

            self._ip_config[ip_ver] = cfg
            self._app.ui.body.update_ip_statuses()
            self._app.ui.body.remove_overlay()
        except (KeyError, ValueError) as exc:
            self._app.show_error_message(str(exc))

    def get_ip_config(self, ip_ver: int) -> dict:
        if ip_ver not in (4, 6):
            raise ValueError(f'Unknown IP version {ip_ver}')
        return attrs.asdict(self._ip_config[ip_ver])

    def set_wifi_config(self, data: dict[str, str]):
        try:
            self._wifi_config = WIFIConfig(ssid=data['ssid'],
                                           psk=data['psk'])
            self._app.ui.body.update_wifi_status()
            self._app.ui.body.remove_overlay()
        except (KeyError, ValueError) as exc:
            self._app.show_error_message(str(exc))

    def get_wifi_config(self) -> Optional[dict[str, str]]:
        if self._wifi_config:
            return attrs.asdict(self._wifi_config)
        else:
            return None

    def to_yaml(self) -> str:
        data = {'hostname': self._hostname}
        for ip_ver in (4, 6):
            tag = 'ipv{}'.format(ip_ver)
            cfg = self.get_ip_config(ip_ver)
            if cfg['method'] == 'static':
                data[tag] = cfg
            else:
                data[tag] = {'method': cfg['method']}

        iface_info = self.get_iface_info(self.get_selected_iface())
        interface = {'name': iface_info.name}
        if iface_info.type == 'bond':
            interface['type'] = iface_info.type
            interface['bond_members'] = iface_info.bond_members
            interface['bond_mode'] = iface_info.bond_mode
            if iface_info.bond_hash_policy:
                interface['bond_hash_policy'] = iface_info.bond_hash_policy
        elif iface_info.type == 'wifi':
            interface['type'] = iface_info.type
            wifi_cfg = self.get_wifi_config()
            interface['wifi_ssid'] = wifi_cfg['ssid']
            interface['wifi_psk'] = wifi_cfg['psk']
        data['interface'] = interface

        yaml_data = yaml.dump({'network': data})
        log.debug('export to yaml: {}'.format(yaml_data))
        return yaml_data
