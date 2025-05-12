#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import logging

from alpaquero.common.utils import write_file
from alpaquero.nmanager.manager import NetworkManager
from alpaquero.nmanager.ip_config import IPConfig4, IPConfig6, is_valid_hostname
from alpaquero.nmanager.wifi_config import WIFIConfig
from .installer import Installer
from .utils import read_key_or_fail

log = logging.getLogger('installers.network')


# network:
#   hostname: your-host-name
#   ipv4:
#     method: static # or dhcp
#     # below tags are only for the static method
#     address: 192.168.0.1/24
#     gateway: 192.168.0.254/24
#     name_servers: [ '1.2.3.4' ]
#     search_domains: [ 'your.search.domain' ]
#   ipv6:
#     method: static # only static method is supported
#     # similar to ipv4
#
#   # Regular ethernet (no '.' in the name and no type specified)
#   interface:
#     name: eth0
#
#   # VLAN over regular ethernet (the '.' in the name)
#   interface:
#     name: eth0.50
#
#   # WiFi interface
#   interface:
#     name: wlan0
#     type: wifi
#     wifi_ssid: WiFiNetworkSSID
#     wifi_psk: Super-Secret-Password
#
#   # Bond interface
#   interface:
#     name: bond0
#     type: bond
#     bond_members: # must be regular ethernet interfaces
#       - eth0
#       - eth1
#     bond_mode: 802.3ad
#     bond_hash_policy: layer2
#


class NetworkInstaller(Installer):
    STUB_MAC_ADDRESS = '00:00:00:00:00:00'
    STUB_VENDOR = 'No vendor'
    STUB_MODEL = 'No model'

    def __init__(self, target_root: str, config: dict, event_receiver):
        self._yaml_tag = 'network'
        super().__init__(name=self._yaml_tag, config=config,
                         event_receiver=event_receiver,
                         data_type=dict, target_root=target_root)

        self._hostname = read_key_or_fail(self._data, 'hostname', str,
                                          error_label=f'{self._yaml_tag}/hostname')
        if not is_valid_hostname(self._hostname):
            raise ValueError('Invalid hostname: {}'.format(self._hostname))
        log.debug('Hostname: {}'.format(self._hostname))

        self._nmanager = NetworkManager()
        self._parse_interface()
        self._parse_ip()

        self.add_package('ifupdown-ng')

    def _parse_interface(self):
        yaml_key = 'interface'
        data = read_key_or_fail(self._data, yaml_key, dict,
                                error_label=f'{self._yaml_tag}/{yaml_key}')
        iface_name = read_key_or_fail(data, 'name', str,
                                      error_label=f'{self._yaml_tag}/{yaml_key}/name')
        if not iface_name:
            raise ValueError('Interface name is empty')

        tokens = iface_name.split('.', maxsplit=1)
        iface = tokens[0]
        vlan_id = 0
        if len(tokens) == 2:
            vlan_id = int(tokens[1])

        iface_type = data.get('type', 'ethernet')
        log.debug('Interface name: {}, type: {}, vlan_id: {}'.format(
            iface_name, iface_type, vlan_id))
        if iface_type == 'ethernet':
            self._nmanager.add_eth_iface(name=iface, mac_address=self.STUB_MAC_ADDRESS,
                                         vendor=self.STUB_VENDOR, model=self.STUB_MODEL)
        elif iface_type == 'bond':
            members = data.get('bond_members', [])
            mode = data.get('bond_mode', '')
            hash_policy = data.get('bond_hash_policy', None)
            log.debug('Bond members: {}, mode: {}, hash_policy: {}'.format(
                members, mode, hash_policy))

            try:
                for member in members:
                    self._nmanager.add_eth_iface(name=member, mac_address=self.STUB_MAC_ADDRESS,
                                                 vendor=self.STUB_VENDOR, model=self.STUB_MODEL)
            except TypeError:
                raise ValueError("Error while adding bond members")

            self._nmanager.add_bond_iface(name=iface, members=members, mode=mode,
                                          hash_policy=hash_policy)
            self.add_package('bonding')
        elif iface_type == 'wifi':
            self._nmanager.add_wifi_iface(name=iface, mac_address=self.STUB_MAC_ADDRESS,
                                          vendor=self.STUB_VENDOR, model=self.STUB_MODEL)
            self._nmanager.set_wifi_config(WIFIConfig(ssid=data.get('wifi_ssid', ''),
                                                      psk=data.get('wifi_psk', '')))
            log.debug('WIFI configuration: {}'.format(self._nmanager.get_wifi_config()))

            self.add_package('ifupdown-ng-wifi')
        else:
            raise ValueError("Unsupported interface type: {}".format(iface_type))

        if vlan_id:
            iface = self._nmanager.add_vlan_iface(base_iface_name=iface, vlan_id=vlan_id)
        self._nmanager.select_iface(iface)
        log.debug('Selected interface: {}'.format(iface))

    def _parse_ip(self):
        for tag in ('ipv4', 'ipv6'):
            if tag not in self._data:
                continue
            ip_data = read_key_or_fail(self._data, tag, dict,
                                       error_label=f'{self._yaml_tag}/{tag}')

            method = ip_data.get('method', '')
            address = ip_data.get('address', '')
            gateway = ip_data.get('gateway', '')
            name_servers = ip_data.get('name_servers', [])
            search_domains = ip_data.get('search_domains', [])

            if tag == 'ipv4':
                self._nmanager.set_ipv4_config(IPConfig4(method=method, address=address, gateway=gateway,
                                                         name_servers=name_servers,
                                                         search_domains=search_domains))
            else:
                self._nmanager.set_ipv6_config(IPConfig6(method=method, address=address, gateway=gateway,
                                                         name_servers=name_servers,
                                                         search_domains=search_domains))

        if (self._nmanager.get_ipv4_config().method == 'disabled') and \
                (self._nmanager.get_ipv6_config().method == 'disabled'):
            raise ValueError('Both IPv4 and IPv6 are not configured')

        log.debug('IPv4 config: {}'.format(self._nmanager.get_ipv4_config()))
        log.debug('IPv6 config: {}'.format(self._nmanager.get_ipv6_config()))

    def write_hostname(self, path: str):
        write_file(path, 'w', data='{}\n'.format(self._hostname))

    def apply(self):
        self.write_hostname(self.abs_target_path('/etc/hostname'))
        self._nmanager.write_resolvconf_file(self.abs_target_path('/etc/resolv.conf'))
        self._nmanager.write_interfaces_file(self.abs_target_path('/etc/network/interfaces'))
