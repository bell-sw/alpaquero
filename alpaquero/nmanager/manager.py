#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from typing import Optional, TypeVar, Type, cast
import re
import os
import logging

import attrs

from .interface import BaseInterface, EthernetInterface, VLANInterface, WIFIInterface, BondInterface
from .interface import InterfaceInfo
from .ip_config import IPConfig4, IPConfig6
from .wifi_config import WIFIConfig
from .bond_config import validate_bond_mode_and_policy
from .identification import identify_device, find_match_in_file, read_one_line
from .utils import get_active_iface_names, wait_iface_gets_ip
from alpaquero.common.utils import run_cmd, write_file

log = logging.getLogger('nmanager.manager')

_InterfaceType = TypeVar('_InterfaceType')

IFUP_TIMEOUT = 30
IFDOWN_TIMEOUT = 10
IP_ASSIGNMENT_TIMEOUT = 60


class NetworkManager:
    def __init__(self):
        self._all_ifaces = set()
        self._available_ifaces = set()
        self._selected_iface: Optional[BaseInterface] = None
        self._ipv4_config = IPConfig4(method='disabled')
        self._ipv6_config = IPConfig6(method='disabled')
        self._reset_ip_configs()
        self._wifi_config: Optional[WIFIConfig] = None
        self._apply_required: bool = False

    def _reset_ip_configs(self):
        self._ipv4_config = IPConfig4(method='disabled')
        self._ipv6_config = IPConfig6(method='disabled')
        log.debug('Reset IP configurations')

    def _iface_by_name(self, name) -> Optional[BaseInterface]:
        for iface in self._all_ifaces:
            if iface.name == name:
                return iface
        return None

    def _iface_by_name_or_fail(self, name) -> BaseInterface:
        iface = self._iface_by_name(name)
        if iface is None:
            raise ValueError(f"Unknown interface '{name}'")
        return iface

    def _check_valid_iface_name(self, name: str):
        if not self.is_valid_iface_name(name):
            raise ValueError("'{}' is not a valid interface name".format(name))

    def _check_iface_is_selected(self):
        if self._selected_iface is None:
            raise RuntimeError('No interface is selected')

    def _check_no_iface_exists(self, name):
        iface = self._iface_by_name(name)
        if iface is not None:
            raise ValueError(f"Interface '{iface.name}' already exists")

    def _check_iface_has_no_constraints(self, iface: BaseInterface):
        for bond_iface in self._all_ifaces_by_type(BondInterface):
            if iface in bond_iface.members:
                raise ValueError("Interface '{}' is a member of '{}'".format(
                    iface.name, bond_iface.name
                ))

        for vlan_iface in self._all_ifaces_by_type(VLANInterface):
            if vlan_iface.base_iface == iface:
                raise ValueError("Interface '{}' is used by VLAN interface '{}'".format(
                    iface.name, vlan_iface.name
                ))

    def _all_ifaces_by_type(self, iface_type: Type[_InterfaceType]) -> set[_InterfaceType]:
        res = set()
        for iface in self._all_ifaces:
            if isinstance(iface, iface_type):
                res.add(iface)
        return res

    def _update_wifi_config_for_selected_iface(self):
        if isinstance(self._selected_iface, WIFIInterface):
            if not self._wifi_config:
                raise ValueError('No WIFI config is set')
            self._selected_iface.ssid = self._wifi_config.ssid
            self._selected_iface.psk = self._wifi_config.psk

    def add_eth_iface(self, name: str, mac_address: str,
                      vendor: str, model: str):
        self._check_valid_iface_name(name)
        self._check_no_iface_exists(name)
        iface = EthernetInterface(name=name, mac_address=mac_address,
                                  vendor=vendor, model=model)
        self._all_ifaces.add(iface)
        self._available_ifaces.add(iface)
        log.debug('Added interface: {}'.format(iface.info))
        return iface.name

    def add_vlan_iface(self, base_iface_name: str, vlan_id: int) -> str:
        base_iface = self._iface_by_name_or_fail(base_iface_name)
        if not isinstance(base_iface, (EthernetInterface, BondInterface)):
            raise ValueError('VLAN tags are supported only on Ethernet and Bond devices')
        iface = VLANInterface(base_iface, vlan_id)
        self._check_no_iface_exists(iface.name)
        self._all_ifaces.add(iface)
        self._available_ifaces.add(iface)
        log.debug('Added interface: {}'.format(iface.info))
        return iface.name

    def add_wifi_iface(self, name: str, mac_address: str,
                       vendor: str, model: str) -> str:
        self._check_valid_iface_name(name)
        self._check_no_iface_exists(name)
        iface = WIFIInterface(name=name, mac_address=mac_address,
                              vendor=vendor, model=model)
        self._all_ifaces.add(iface)
        self._available_ifaces.add(iface)
        log.debug('Added interface: {}'.format(iface.info))
        return iface.name

    def add_bond_iface(self, name: str, members: list[str],
                       mode: str, hash_policy: Optional[str] = None) -> str:
        self._check_valid_iface_name(name)
        self._check_no_iface_exists(name)
        validate_bond_mode_and_policy(mode, hash_policy)
        if not members:
            raise ValueError('Empty members list')
        member_ifaces = []
        for member in members:
            member_iface = self._iface_by_name_or_fail(member)
            if not isinstance(member_iface, EthernetInterface):
                raise ValueError("'{}' is not an Ethernet interface".format(member_iface.name))
            self._check_iface_has_no_constraints(member_iface)
            member_ifaces.append(cast(EthernetInterface, member_iface))

        iface = BondInterface(name=name, members=member_ifaces,
                              mode=mode, hash_policy=hash_policy)
        self._all_ifaces.add(iface)
        self._available_ifaces.add(iface)
        self._available_ifaces.difference_update(member_ifaces)
        log.debug('Added interface: {}'.format(iface.info))
        return iface.name

    def del_iface(self, name):
        iface_to_delete = self._iface_by_name_or_fail(name)
        if self._selected_iface == iface_to_delete:
            self._selected_iface = None

        if isinstance(iface_to_delete, (EthernetInterface, BondInterface)):
            self._check_iface_has_no_constraints(iface_to_delete)
        if isinstance(iface_to_delete, BondInterface):
            self._available_ifaces.update(iface_to_delete.members)

        self._all_ifaces.remove(iface_to_delete)
        self._available_ifaces.remove(iface_to_delete)
        log.debug('Deleted interface: {}'.format(iface_to_delete.info))

    # interfaces available for selection/configuration
    def get_available_ifaces(self) -> set[str]:
        return set((iface.name for iface in self._available_ifaces))

    def get_bond_candidates(self) -> set[str]:
        res = set()

        for iface in self._available_ifaces:
            if isinstance(iface, EthernetInterface):
                try:
                    self._check_iface_has_no_constraints(iface)
                    res.add(iface)
                except ValueError:
                    pass

        return set((iface.name for iface in res))

    def select_iface(self, name):
        new_iface = self._iface_by_name_or_fail(name)
        if new_iface != self._selected_iface:
            self._selected_iface = new_iface
            self._apply_required = True
            log.debug('Selected interface: {}'.format(self._selected_iface.info))
            self._reset_ip_configs()

    def get_selected_iface(self) -> Optional[str]:
        if self._selected_iface:
            return self._selected_iface.name
        return None

    def get_iface_info(self, name) -> InterfaceInfo:
        iface = self._iface_by_name_or_fail(name)
        return iface.info

    def set_wifi_config(self, config: WIFIConfig):
        new_config = attrs.evolve(config)
        if new_config != self._wifi_config:
            self._wifi_config = new_config
            self._apply_required = True
            log.debug('Set WIFI config: {}'.format(self._wifi_config))

    def get_wifi_config(self) -> Optional[WIFIConfig]:
        return self._wifi_config

    def set_ipv4_config(self, config: IPConfig4):
        self._check_iface_is_selected()
        new_config = attrs.evolve(config)
        if new_config != self._ipv4_config:
            self._ipv4_config = new_config
            self._apply_required = True
            log.debug('Set IPv4 config: {}'.format(self._ipv4_config))

    def set_ipv6_config(self, config: IPConfig6):
        self._check_iface_is_selected()
        new_config = attrs.evolve(config)
        if new_config != self._ipv6_config:
            self._ipv6_config = new_config
            self._apply_required = True
            log.debug('Set IPv6 config: {}'.format(self._ipv6_config))

    def get_ipv4_config(self) -> IPConfig4:
        self._check_iface_is_selected()
        return attrs.evolve(self._ipv4_config)

    def get_ipv6_config(self) -> IPConfig6:
        self._check_iface_is_selected()
        return attrs.evolve(self._ipv6_config)

    def write_resolvconf_file(self, path: str = '/etc/resolv.conf'):
        log.debug('Writing {}'.format(path))
        self._check_iface_is_selected()

        name_servers = []
        search_domains = []
        if self._ipv4_config.method == 'static':
            name_servers.extend(self._ipv4_config.name_servers)
            search_domains.extend(self._ipv4_config.search_domains)
        if self._ipv6_config.method == 'static':
            name_servers.extend(self._ipv6_config.name_servers)
            search_domains.extend(self._ipv6_config.search_domains)

        lines = []
        if name_servers:
            lines.extend((f'nameserver {n}\n' for n in name_servers))
            if search_domains:
                lines.append('search {}\n'.format((' '.join(search_domains))))
        write_file(path, 'w', data=''.join(lines))

    def write_interfaces_file(self, path: str = '/etc/network/interfaces'):
        log.debug('Writing {}'.format(path))
        self._check_iface_is_selected()
        self._update_wifi_config_for_selected_iface()

        lines = ['auto lo',
                 'iface lo inet loopback']
        if (self._ipv4_config.method != 'disabled') or (self._ipv6_config.method != 'disabled'):
            lines.append('')
            lines.append('auto {}'.format(self._selected_iface.name))
            lines.append('iface {}'.format(self._selected_iface.name))

            interface_lines = []
            interface_lines.extend(self._selected_iface.get_interface_lines())
            interface_lines.extend(self._ipv4_config.get_interface_lines())
            interface_lines.extend(self._ipv6_config.get_interface_lines())
            lines.extend((f'    {line}' for line in interface_lines))
        write_file(path, 'w', data='\n'.join(lines) + '\n')

    @property
    def apply_required(self) -> bool:
        return self._apply_required

    def apply(self):
        log.debug('Applying configuration')
        self._check_iface_is_selected()
        if (self._ipv4_config.method == 'disabled') and (self._ipv6_config.method == 'disabled'):
            raise RuntimeError("No IPv4 or IPv6 is configured on interface '{}'".format(
                self._selected_iface.name
            ))

        self._update_wifi_config_for_selected_iface()

        # Stop all active interfaces
        while True:
            active_ifaces = get_active_iface_names()
            if not active_ifaces:
                break

            stopped_iface = None
            for iface in active_ifaces:
                res = run_cmd(['ifdown', iface], timeout=IFDOWN_TIMEOUT, ignore_status=True)
                if res.returncode == 0:
                    stopped_iface = iface
            if not stopped_iface:
                raise RuntimeError('Could not stop a single interface')

        self.write_resolvconf_file()
        self.write_interfaces_file()

        run_cmd(['ifup', 'lo'], timeout=IFUP_TIMEOUT)
        run_cmd(['ifup', self._selected_iface.name], timeout=IFUP_TIMEOUT)

        if self._ipv4_config.method != 'disabled':
            wait_iface_gets_ip(self._selected_iface.name,
                               ip_ver=4, timeout=IP_ASSIGNMENT_TIMEOUT)
        if self._ipv6_config.method != 'disabled':
            wait_iface_gets_ip(self._selected_iface.name,
                               ip_ver=6, timeout=IP_ASSIGNMENT_TIMEOUT)

        self._apply_required = False

    def add_host_ifaces(self):
        log.debug('Adding host network interfaces')
        for entry in os.scandir('/sys/class/net'):
            # A physical NIC contains a 'device' link to the actual device
            if not os.path.islink(os.path.join(entry.path, 'device')):
                continue

            uevent_path = os.path.join(entry.path, 'uevent')
            if not os.path.isfile(uevent_path):
                continue
            devtype = None
            m = find_match_in_file(r'^DEVTYPE=(.+)$', uevent_path)
            if m:
                devtype = m.group(1)

            if (devtype is not None) and (devtype != 'wlan'):
                continue

            mac_address_path = os.path.join(entry.path, 'address')
            mac_address = read_one_line(mac_address_path)
            if not mac_address:
                raise RuntimeError("No MAC address as '{}' is empty".format(mac_address_path))

            device_id = identify_device(os.path.join(entry.path, 'device'))
            iface_name = entry.name

            if devtype is None:
                self.add_eth_iface(iface_name, mac_address=mac_address,
                                   vendor=device_id.vendor, model=device_id.model)
            elif devtype == 'wlan':
                self.add_wifi_iface(iface_name, mac_address=mac_address,
                                    vendor=device_id.vendor, model=device_id.model)

    @staticmethod
    def is_valid_iface_name(name: str) -> bool:
        # These checks are from check_ifname() from
        # https://git.kernel.org/pub/scm/network/iproute2/iproute2.git/tree/lib/utils.c
        return bool(re.match(r'^[^\s/]{1,16}$', name))
