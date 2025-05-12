#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
from typing import TYPE_CHECKING

import pytest

from alpaquero.installers.installer import InstallerException
from alpaquero.installers.network import NetworkInstaller
from .utils import new_installer

if TYPE_CHECKING:
    from alpaquero.nmanager.manager import NetworkManager


@pytest.fixture
def mock_host_ifaces(monkeypatch):
    def add_host_ifaces(self: NetworkManager):
        self.add_eth_iface('eth0', mac_address='00:11:22:33:44:55',
                           vendor='Some vendor', model='Some model')
        self.add_eth_iface('eth1', mac_address='11:22:33:44:55:66',
                           vendor='Some vendor', model='Some model')
        self.add_wifi_iface('wlan0', mac_address='00:11:22:33:44:55',
                            vendor='Some vendor', model='Some model')

    monkeypatch.setattr('alpaquero.nmanager.manager.NetworkManager.add_host_ifaces',
                        add_host_ifaces)


@pytest.fixture
def target_root(tmp_path):
    res = tmp_path / 'target_root'
    (res / 'etc/network').mkdir(parents=True)
    return res


def static_ipv4_config():
    return {'network': {
        'hostname': 'some-host-name',
        'ipv4': {
            'method': 'static',
            'address': '192.168.0.1/24',
            'gateway': '192.168.0.254',
            'name_servers': ['1.2.3.4'],
            'search_domains': ['domain1', 'domain2.com'],
        },
        'interface': {'name': 'eth0'},
    }}


def dhcp_ipv4_config():
    return {'network': {
        'hostname': 'some-host-name',
        'ipv4': {'method': 'dhcp'},
        'interface': {'name': 'eth0'},
    }}


def static_ipv6_config():
    return {'network': {
        'hostname': 'some-host-name',
        'ipv6': {
            'method': 'static',
            'address': '2001:db8:abcd:0012::1/64',
            'gateway': '2001:db8:abcd:0012::2',
            'name_servers': ['2001:db8:abcd:0012::3'],
            'search_domains': ['domain1', 'domain2.com']
        },
        'interface': {'name': 'eth0'}
    }}


def bond_config():
    config = dhcp_ipv4_config()
    config['network']['interface'] = {  # type: ignore
        'name': 'bond0',
        'type': 'bond',
        'bond_members': ['eth0', 'eth1'],
        'bond_mode': 'balance-rr',
    }
    return config


def vlan_config():
    config = dhcp_ipv4_config()
    config['network']['interface']['name'] = 'eth0.99'
    return config


def wifi_config():
    config = dhcp_ipv4_config()
    config['network']['interface'] = {  # type: ignore
        'name': 'wlan0',
        'type': 'wifi',
        'wifi_ssid': 'wifi-ssid',
        'wifi_psk': 'wifi-psk',
    }
    return config


def create_installer(config: dict, **kwargs) -> NetworkInstaller:
    return new_installer(NetworkInstaller, config=config, **kwargs)


def test_no_network():
    with pytest.raises(InstallerException):
        create_installer({})


def test_hostname(mock_host_ifaces):
    with pytest.raises(ValueError, match=r'(?i)invalid hostname'):
        create_installer({'network': {
            'ipv4': {'method': 'dhcp'},
            'ipv6': {'method': 'dhcp'},
            'interface': {'name': 'eth0'}
        }})

    for hostname in (' ', 'host name', '_hostname', '-hostname', 'hostname.'):
        with pytest.raises(ValueError, match=r'(?i)invalid hostname'):
            create_installer({'network': {
                'hostname': hostname,
                'ipv4': {'method': 'dhcp'},
                'ipv6': {'method': 'dhcp'},
                'interface': {'name': 'eth0'}
            }})


def test_ipv4_dhcp(mock_host_ifaces):
    create_installer(dhcp_ipv4_config())


def test_ipv4_invalid_format(mock_host_ifaces):
    config = dhcp_ipv4_config()
    config['network']['ipv4'] = 'invalid format'  # type: ignore
    with pytest.raises(ValueError, match="'network/ipv4'"):
        create_installer(config)


def test_ipv4_unsupported_method(mock_host_ifaces):
    config = dhcp_ipv4_config()
    config['network']['ipv4'] = {'method': 'unsupported method'}  # type: ignore
    with pytest.raises(ValueError):
        create_installer(config)


def test_ipv4_static(mock_host_ifaces):
    create_installer(static_ipv4_config())


def test_ipv4_address_wo_mask(mock_host_ifaces):
    config = static_ipv4_config()
    config['network']['ipv4']['address'] = '192.168.0.1'
    with pytest.raises(ValueError):
        create_installer(config)


def test_ipv4_address_gateway_in_different_networks(mock_host_ifaces):
    config = static_ipv4_config()
    config['network']['ipv4']['gateway'] = '192.168.1.254'
    with pytest.raises(ValueError):
        create_installer(config)


def test_ipv4_address_gateway_are_identical(mock_host_ifaces):
    config = static_ipv4_config()
    config['network']['ipv4']['gateway'] = '192.168.0.1'
    with pytest.raises(ValueError):
        create_installer(config)


def test_ipv4_name_servers_empty(mock_host_ifaces):
    config = static_ipv4_config()
    config['network']['ipv4']['name_servers'] = []
    with pytest.raises(ValueError, match=r'(?i)no name servers'):
        create_installer(config)


def test_ipv4_one_name_server_empty(mock_host_ifaces):
    config = static_ipv4_config()
    config['network']['ipv4']['name_servers'] = ['1.2.3.4', '']
    with pytest.raises(ValueError, match='empty'):
        create_installer(config)


def test_ipv4_name_servers_invalid_format(mock_host_ifaces):
    config = static_ipv4_config()
    config['network']['ipv4']['name_servers'] = 'invalid format'  # type: ignore
    with pytest.raises(TypeError):
        create_installer(config)


def test_ipv4_name_servers_domain_not_address(mock_host_ifaces):
    config = static_ipv4_config()
    config['network']['ipv4']['name_servers'] = ['domain.not.address']
    with pytest.raises(ValueError):
        create_installer(config)


def test_ipv4_search_domains_invalid_format(mock_host_ifaces):
    config = static_ipv4_config()
    config['network']['ipv4']['search_domains'] = 'invalid format'  # type: ignore
    with pytest.raises(TypeError):
        create_installer(config)


def test_no_ipv4_and_ipv6(mock_host_ifaces):
    config = dhcp_ipv4_config()
    del config['network']['ipv4']
    with pytest.raises(ValueError, match=r'(?i)not configured'):
        create_installer(config)


def test_ipv6_static(mock_host_ifaces):
    create_installer(static_ipv6_config())


def test_ipv6_address_wo_mask(mock_host_ifaces):
    config = static_ipv6_config()
    config['network']['ipv6']['address'] = '2001:db8:abcd:0012::1'
    with pytest.raises(ValueError):
        create_installer(config)


def test_ipv6_address_gateway_in_different_networks(mock_host_ifaces):
    config = static_ipv6_config()
    config['network']['ipv6']['gateway'] = '2001:db8:abcd:0013::2'
    with pytest.raises(ValueError):
        create_installer(config)


def test_ipv6_address_gateway_are_identical(mock_host_ifaces):
    config = static_ipv6_config()
    config['network']['ipv6']['gateway'] = '2001:db8:abcd:0012::1'
    with pytest.raises(ValueError):
        create_installer(config)


def test_ipv6_invalid_format(mock_host_ifaces):
    config = static_ipv6_config()
    config['network']['ipv6'] = 'invalid format'  # type: ignore
    with pytest.raises(ValueError, match="'network/ipv6'"):
        create_installer(config)


def test_ipv6_unsupported_method(mock_host_ifaces):
    config = static_ipv6_config()
    config['network']['ipv6'] = {'method': 'dhcp'}  # type: ignore
    with pytest.raises(ValueError):
        create_installer(config)


def test_no_interface(mock_host_ifaces):
    config = dhcp_ipv4_config()
    del config['network']['interface']
    with pytest.raises(ValueError, match=r'(?i)interface'):
        create_installer(config)


def test_invalid_interface_type(mock_host_ifaces):
    config = dhcp_ipv4_config()
    config['network']['interface'] = {  # type: ignore
        'name': 'eth0',
        'type': 'invalid type',
    }
    with pytest.raises(ValueError, match=r'(?i)unsupported interface type'):
        create_installer(config)


def test_ethernet_interface(mock_host_ifaces):
    installer = create_installer(dhcp_ipv4_config())
    assert 'ifupdown-ng' in installer.packages


def test_vlan_interface(mock_host_ifaces):
    config = dhcp_ipv4_config()
    config['network']['interface'] = {'name': 'eth0.50'}  # type: ignore
    create_installer(config)


def test_bond_interface(mock_host_ifaces):
    installer = create_installer(bond_config())
    assert 'bonding' in installer.packages


def test_bond_interface_invalid_mode(mock_host_ifaces):
    config = bond_config()
    config['network']['interface']['bond_mode'] = 'unsupported mode'
    with pytest.raises(ValueError, match=r'(?i)unknown bond mode'):
        create_installer(config)


def test_bond_interface_invalid_members_format(mock_host_ifaces):
    config = bond_config()
    config['network']['interface']['bond_members'] = False
    with pytest.raises(ValueError, match=r'(?i)Error while adding bond members'):
        create_installer(config)


def test_bond_interface_hash_policies(mock_host_ifaces):
    bond_modes = ('balance-rr', 'active-backup', 'balance-xor', 'broadcast',
                  '802.3ad', 'balance-tlb', 'balance-alb')
    bond_modes_with_hash_policy = ('balance-alb', 'balance-tlb', 'balance-xor',
                                   '802.3ad')
    hash_policies = ('layer2', 'layer3+4', 'layer2+3', 'encap2+3', 'encap3+4')

    for bond_mode in bond_modes:
        config = bond_config()
        config['network']['interface']['bond_mode'] = bond_mode

        for hash_policy in hash_policies:
            config['network']['interface']['bond_hash_policy'] = hash_policy
            if bond_mode in bond_modes_with_hash_policy:
                create_installer(config)
            else:
                with pytest.raises(ValueError, match=r'(?i)unknown policy'):
                    create_installer(config)

    for bond_mode in bond_modes_with_hash_policy:
        config = bond_config()
        config['network']['interface']['bond_mode'] = bond_mode
        config['network']['interface']['bond_hash_policy'] = 'unsupported hash policy'
        with pytest.raises(ValueError, match=r'(?i)unknown policy'):
            create_installer(config)

    for bond_mode in (set(bond_modes) - set(bond_modes_with_hash_policy)):
        config = bond_config()
        config['network']['interface']['bond_mode'] = bond_mode
        create_installer(config)


def test_wifi_interface(mock_host_ifaces):
    installer = create_installer(wifi_config())
    assert 'ifupdown-ng-wifi' in installer.packages


def test_wifi_no_ssid(mock_host_ifaces):
    config = wifi_config()
    del config['network']['interface']['wifi_ssid']
    with pytest.raises(ValueError, match=r'(?i)ssid'):
        create_installer(config)


def test_wifi_invalid_ssid(mock_host_ifaces):
    config = wifi_config()

    for ssid in ('', 'x', 'x' * (32 + 1)):
        config['network']['interface']['wifi_ssid'] = ssid
        with pytest.raises(ValueError, match=r'(?i)must be from'):
            create_installer(config)

    config['network']['interface']['wifi_ssid'] = 'ssid_with_#'
    with pytest.raises(ValueError, match=r'(?i)must not contain #'):
        create_installer(config)


def test_wifi_no_psk(mock_host_ifaces):
    config = wifi_config()
    del config['network']['interface']['wifi_psk']
    with pytest.raises(ValueError, match=r'(?i)psk'):
        create_installer(config)


def test_wifi_invalid_psk(mock_host_ifaces):
    config = wifi_config()

    for psk in ('', 'x' * (8 - 1), 'x' * (63 + 1)):
        config['network']['interface']['wifi_psk'] = psk
        with pytest.raises(ValueError, match=r'(?i)must be from'):
            create_installer(config)

    config['network']['interface']['wifi_psk'] = 'psk_with_symbol_#'
    with pytest.raises(ValueError, match=r'(?i)must not contain #'):
        create_installer(config)


def test_static_ipv4_config_apply(target_root):
    installer = create_installer(config=static_ipv4_config(), target_root=target_root)
    installer.apply()

    with open(target_root / 'etc/hostname') as file:
        assert file.read() == 'some-host-name\n'
    with open(target_root / 'etc/resolv.conf') as file:
        assert file.read() == '''nameserver 1.2.3.4
search domain1 domain2.com
'''
    with open(target_root / 'etc/network/interfaces') as file:
        assert file.read() == '''auto lo
iface lo inet loopback

auto eth0
iface eth0
    use static
    address 192.168.0.1/24
    gateway 192.168.0.254
'''


def test_dhcp_ipv4_config_apply(target_root):
    installer = create_installer(config=dhcp_ipv4_config(), target_root=target_root)
    installer.apply()

    with open(target_root / 'etc/hostname') as file:
        assert file.read() == 'some-host-name\n'
    with open(target_root / 'etc/resolv.conf') as file:
        assert file.read() == ''
    with open(target_root / 'etc/network/interfaces') as file:
        assert file.read() == '''auto lo
iface lo inet loopback

auto eth0
iface eth0
    use dhcp
'''


def test_static_ipv6_config_apply(target_root):
    installer = create_installer(config=static_ipv6_config(), target_root=target_root)
    installer.apply()

    with open(target_root / 'etc/hostname') as file:
        assert file.read() == 'some-host-name\n'
    with open(target_root / 'etc/resolv.conf') as file:
        assert file.read() == '''nameserver 2001:db8:abcd:12::3
search domain1 domain2.com
'''
    with open(target_root / 'etc/network/interfaces') as file:
        assert file.read() == '''auto lo
iface lo inet loopback

auto eth0
iface eth0
    use static
    address 2001:db8:abcd:12::1/64
    gateway 2001:db8:abcd:12::2
'''


def test_vlan_config_apply(target_root):
    installer = create_installer(config=vlan_config(), target_root=target_root)
    installer.apply()

    with open(target_root / 'etc/hostname') as file:
        assert file.read() == 'some-host-name\n'
    with open(target_root / 'etc/resolv.conf') as file:
        assert file.read() == ''
    with open(target_root / 'etc/network/interfaces') as file:
        assert file.read() == '''auto lo
iface lo inet loopback

auto eth0.99
iface eth0.99
    use dhcp
'''


def test_bond_config_apply(target_root):
    installer = create_installer(config=bond_config(), target_root=target_root)
    installer.apply()

    with open(target_root / 'etc/hostname') as file:
        assert file.read() == 'some-host-name\n'
    with open(target_root / 'etc/resolv.conf') as file:
        assert file.read() == ''
    with open(target_root / 'etc/network/interfaces') as file:
        assert file.read() == '''auto lo
iface lo inet loopback

auto bond0
iface bond0
    bond-members eth0 eth1
    bond-mode balance-rr
    use dhcp
'''


def test_wifi_config_apply(target_root):
    installer = create_installer(config=wifi_config(), target_root=target_root)
    installer.apply()

    with open(target_root / 'etc/hostname') as file:
        assert file.read() == 'some-host-name\n'
    with open(target_root / 'etc/resolv.conf') as file:
        assert file.read() == ''
    with open(target_root / 'etc/network/interfaces') as file:
        assert file.read() == '''auto lo
iface lo inet loopback

auto wlan0
iface wlan0
    wifi-ssid wifi-ssid
    wifi-psk wifi-psk
    use dhcp
'''
