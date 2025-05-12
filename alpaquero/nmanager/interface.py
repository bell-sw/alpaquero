#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from typing import Optional
import re
import abc

import attrs

from .wifi_config import validate_wifi_ssid, validate_wifi_psk
from .bond_config import validate_bond_mode_and_policy


def validate_mac_address(mac_address: str):
    if not re.match(r'^[0-9a-zA-Z]{2}(:[0-9a-zA-Z]{2}){5}$', mac_address):
        raise ValueError("'{}' is an invalid MAC address".format(mac_address))


@attrs.define
class InterfaceInfo:
    name: str = ''
    type: str = ''

    # ethernet and wifi
    mac_address: str = ''
    vendor: str = ''
    model: str = ''

    # vlan
    base_iface: str = ''
    vlan_id: int = 0

    # wifi
    ssid: str = ''
    psk: str = ''

    # bond
    bond_mode: str = ''
    bond_hash_policy: str = ''
    bond_members: list[str] = attrs.field(default=attrs.Factory(list))


class BaseInterface(abc.ABC):
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    @abc.abstractmethod
    def info(self) -> InterfaceInfo:
        pass

    def get_interface_lines(self) -> list[str]:
        return []


class EthernetInterface(BaseInterface):
    def __init__(self, name: str, mac_address: str,
                 vendor: str, model: str):
        super().__init__(name)
        validate_mac_address(mac_address)
        self._mac_address = mac_address
        self._vendor = vendor
        self._model = model

    @property
    def mac_address(self) -> str:
        return self._mac_address

    @property
    def vendor(self) -> str:
        return self._vendor

    @property
    def model(self) -> str:
        return self._model

    @property
    def info(self) -> InterfaceInfo:
        return InterfaceInfo(name=self.name,
                             type='ethernet',
                             mac_address=self.mac_address,
                             vendor=self.vendor,
                             model=self.model)


class VLANInterface(BaseInterface):
    def __init__(self, base_iface: BaseInterface, vlan_id: int):
        if (vlan_id < 1) or (vlan_id > 4095):
            raise ValueError('VLAN ID must be within [1; 4095]')
        name = f'{base_iface.name}.{vlan_id}'
        super().__init__(name)
        self._base_iface = base_iface
        self._vlan_id = int(vlan_id)

    @property
    def base_iface(self) -> BaseInterface:
        return self._base_iface

    @property
    def vlan_id(self) -> int:
        return self._vlan_id

    @property
    def info(self) -> InterfaceInfo:
        return InterfaceInfo(name=self.name,
                             type='vlan',
                             base_iface=self.base_iface.name,
                             vlan_id=self.vlan_id)

    def get_interface_lines(self) -> list[str]:
        return self.base_iface.get_interface_lines()


# We keep SSID and PSK attributes as interface properties
# for simplicity as in the installer we don't need to connect
# to more than one wireless network simultaneously
class WIFIInterface(BaseInterface):
    def __init__(self, name: str, mac_address: str,
                 vendor: str, model: str):
        super().__init__(name)
        validate_mac_address(mac_address)
        self._mac_address = mac_address
        self._vendor = vendor
        self._model = model
        self._ssid = ''
        self._psk = ''

    @property
    def mac_address(self) -> str:
        return self._mac_address

    @property
    def vendor(self) -> str:
        return self._vendor

    @property
    def model(self) -> str:
        return self._model

    @property
    def ssid(self) -> str:
        return self._ssid

    @ssid.setter
    def ssid(self, value: str):
        validate_wifi_ssid(value)
        self._ssid = value

    @property
    def psk(self) -> str:
        return self._psk

    @psk.setter
    def psk(self, value: str):
        validate_wifi_psk(value)
        self._psk = value

    @property
    def info(self) -> InterfaceInfo:
        return InterfaceInfo(name=self.name,
                             type='wifi',
                             mac_address=self.mac_address,
                             vendor=self.vendor,
                             model=self.model,
                             ssid=self.ssid,
                             psk=self.psk)

    def get_interface_lines(self) -> list[str]:
        if not self.ssid:
            raise ValueError('No SSID is set on device {}'.format(self.name))
        if not self.psk:
            raise ValueError('No WPA2 PSK is set on device {}'.format(self.name))

        return ['wifi-ssid {}'.format(self.ssid),
                'wifi-psk {}'.format(self.psk)]


class BondInterface(BaseInterface):
    def __init__(self, name: str, members: list[EthernetInterface],
                 mode: str, hash_policy: Optional[str] = None):
        super().__init__(name)
        if not members:
            raise ValueError('No member interfaces specified')
        for member in members:
            if not isinstance(member, EthernetInterface):
                raise ValueError('Member {} is not an Ethernet interface'.format(member.name))
        self._members = members[:]
        validate_bond_mode_and_policy(mode, hash_policy)
        self._mode = mode
        self._hash_policy = hash_policy

    @property
    def members(self) -> list[EthernetInterface]:
        return self._members[:]

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def hash_policy(self) -> Optional[str]:
        return self._hash_policy

    @property
    def info(self) -> InterfaceInfo:
        return InterfaceInfo(name=self.name,
                             type='bond',
                             bond_mode=self.mode,
                             bond_hash_policy=self.hash_policy,
                             bond_members=[iface.name for iface in self.members])

    def get_interface_lines(self) -> list[str]:
        res = ['bond-members {}'.format(' '.join(iface.name for iface in self.members)),
               'bond-mode {}'.format(self.mode)]
        if self.hash_policy:
            res.append('bond-xmit-hash-policy {}'.format(self.hash_policy))
        return res
