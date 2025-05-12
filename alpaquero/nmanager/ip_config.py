#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import re
import ipaddress

import attrs

DOMAIN_REGEX = r'^((?!-)[A-Za-z0-9-]{1,63}(?<!-).)*(?!-)[A-Za-z0-9-]{1,63}(?<!-)$'
HOSTNAME_REGEX = r'^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$'


def is_valid_domain(domain: str) -> bool:
    return bool(re.match(DOMAIN_REGEX, domain))


def is_valid_hostname(hostname: str) -> bool:
    return bool(re.match(HOSTNAME_REGEX, hostname))


@attrs.define
class IPConfig:
    _IP_ADDRESS_CLS = type
    _IP_INTERFACE_CLS = type

    method: str

    # for mode == 'static'
    address: str = attrs.field(default='', validator=attrs.validators.instance_of(str))
    gateway: str = attrs.field(default='', validator=attrs.validators.instance_of(str))
    name_servers: list[str] = attrs.field(default=attrs.Factory(list),
                                          validator=attrs.validators.instance_of(list))
    search_domains: list[str] = attrs.field(default=attrs.Factory(list),
                                            validator=attrs.validators.instance_of(list))

    @staticmethod
    def supported_modes() -> list[str]:
        return []

    # TODO: there is no validation if one decides to assign to one of the fields
    # after an IPConfig object gets instantiated
    def __attrs_post_init__(self):
        if self.method not in self.supported_methods():
            raise ValueError('Unsupported method: {}'.format(self.method))

        validator = getattr(self, '_validate_method_{}'.format(self.method), None)
        if validator:
            validator()

    def _validate_method_dhcp(self):
        pass

    def _validate_method_disabled(self):
        pass

    def _validate_method_static(self):
        try:
            address_ip = self._IP_INTERFACE_CLS(self.address)
            gateway_ip = self._IP_ADDRESS_CLS(self.gateway)
        except ipaddress.AddressValueError as exc:
            raise ValueError(str(exc)) from None
        if address_ip.network.num_addresses == 1:
            raise ValueError('Only 1 host in the network: {}'.format(address_ip))
        if gateway_ip == address_ip.ip:
            raise ValueError('Address and gateway are identical: {}'.format(address_ip.ip))
        network = address_ip.network
        if gateway_ip not in network:
            raise ValueError("Gateway '{}' is not on network '{}'".format(str(gateway_ip), str(network)))
        self.address = str(address_ip)
        self.gateway = str(gateway_ip)

        name_servers = []
        for server in self.name_servers:
            if not isinstance(server, str):
                raise ValueError('Non-str name server value: {}'.format(server))
            server = server.strip()
            if not server:
                raise ValueError('An empty name server was passed')
            try:
                server_ip = self._IP_ADDRESS_CLS(server)
            except ipaddress.AddressValueError as exc:
                raise ValueError("Invalid name server: {}".format(str(exc))) from None
            name_servers.append(str(server_ip))
        if not name_servers:
            raise ValueError('No name servers configured')
        self.name_servers = name_servers

        search_domains = []
        for domain in self.search_domains:
            if not isinstance(domain, str):
                raise ValueError('Non-str domain value: {}'.format(domain))
            if not domain:
                continue
            if not re.match(DOMAIN_REGEX, domain):
                raise ValueError('Invalid domain: {}'.format(domain))
            search_domains.append(domain)
        self.search_domains = search_domains

    def get_interface_lines(self) -> list[str]:
        if self.method == 'dhcp':
            return ['use dhcp']
        elif self.method == 'static':
            return ['use static',
                    'address {}'.format(self.address),
                    'gateway {}'.format(self.gateway)]
        else:
            return []


class IPConfig4(IPConfig):
    _IP_ADDRESS_CLS = ipaddress.IPv4Address
    _IP_INTERFACE_CLS = ipaddress.IPv4Interface

    @staticmethod
    def supported_methods() -> list[str]:
        return ['dhcp', 'disabled', 'static']


class IPConfig6(IPConfig):
    _IP_ADDRESS_CLS = ipaddress.IPv6Address
    _IP_INTERFACE_CLS = ipaddress.IPv6Interface

    @staticmethod
    def supported_methods() -> list[str]:
        return ['disabled', 'static']
