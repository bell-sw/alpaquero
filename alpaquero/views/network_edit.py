#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
from typing import TYPE_CHECKING
import ipaddress

import urwid

from subiquitycore.ui.form import Form, SubForm, StringField, SubFormField, ChoiceField
from subiquitycore.ui.container import Pile
from subiquitycore.ui.stretchy import Stretchy

from alpaquero.nmanager.ip_config import is_valid_domain

if TYPE_CHECKING:
    from .network_vlan import NetworkView

IP_INTERFACE_CLS = {4: ipaddress.IPv4Interface,
                    6: ipaddress.IPv6Interface}
IP_INTERFACE_SUFFIX_NAME = {4: 'netmask',
                            6: 'prefix'}
IP_ADDRESS_CLS = {4: ipaddress.IPv4Address,
                  6: ipaddress.IPv6Address}


def _clean_address(ip_ver: int):
    def func(self, value):
        suffix = IP_INTERFACE_SUFFIX_NAME[ip_ver]

        if '/' not in value:
            raise ValueError(f'No {suffix} specified')

        try:
            addr = IP_INTERFACE_CLS[ip_ver](value)
        except ipaddress.AddressValueError:
            raise ValueError(f'Must be in the address/{suffix} format') from None
        except ipaddress.NetmaskValueError:
            raise ValueError(f'Invalid {suffix} specified') from None

        if addr.network.num_addresses == 1:
            raise ValueError(f'The {suffix} describes a single-host network')

        return value
    return func


def _clean_gateway(ip_ver: int):
    def func(self, value):
        try:
            IP_ADDRESS_CLS[ip_ver](value)
        except ipaddress.AddressValueError:
            raise ValueError('Invalid address') from None
        return value
    return func


def _clean_name_servers(ip_ver: int):
    def func(self, value):
        for server in value.split(','):
            try:
                IP_ADDRESS_CLS[ip_ver](server)
            except ipaddress.AddressValueError:
                raise ValueError("'{}' is not an IPv{} address".format(server, ip_ver)) from None
        return value
    return func


def _clean_search_domains(ip_ver: int):
    def func(self, value):
        if not value:
            return value
        for domain in value.split(','):
            if not is_valid_domain(domain):
                raise ValueError("'{}' is not a valid domain".format(domain))
        return value
    return func


# This duplication of ipv4 and ipv6 forms are only because I could not
# make a parent IPStaticForm with IP_INTERFACE_CLS and IP_ADDRESS_CLS
# as class members and subclass ipv4 and ipv6 variants. It didn't work.
class IPv4StaticForm(SubForm):
    address = StringField('Address:', help=f'IP address in the address/{IP_INTERFACE_SUFFIX_NAME[4]} format')
    gateway = StringField('Gateway:')
    name_servers = StringField('Name servers:', help='IP addresses, comma separated')
    search_domains = StringField('Search domains:', help='Domains, comma separated')

    clean_address = _clean_address(4)
    clean_gateway = _clean_gateway(4)
    clean_name_servers = _clean_name_servers(4)
    clean_search_domains = _clean_search_domains(4)


class IPv6StaticForm(SubForm):
    address = StringField('Address:', help=f'IP address in the address/{IP_INTERFACE_SUFFIX_NAME[6]} format')
    gateway = StringField('Gateway:')
    name_servers = StringField('Name servers:', help='IP addresses, comma separated')
    search_domains = StringField('Search domains:', help='Domains, comma separated')

    clean_address = _clean_address(6)
    clean_gateway = _clean_gateway(6)
    clean_name_servers = _clean_name_servers(6)
    clean_search_domains = _clean_search_domains(6)


class EditIPv4Form(Form):
    ok_label = 'Save'

    method = ChoiceField('IPv4:', choices=[('DHCP', True, 'dhcp'),
                                           ('Static', True, 'static'),
                                           ('Disabled', True, 'disabled')])
    static_subform = SubFormField(IPv4StaticForm, '')


class EditIPv6Form(Form):
    ok_label = 'Save'

    method = ChoiceField('IPv6:', choices=[('Static', True, 'static'),
                                           ('Disabled', True, 'disabled')])
    static_subform = SubFormField(IPv6StaticForm, '')


class EditIPStretchy(Stretchy):
    def __init__(self, parent: NetworkView, ip_ver: int):
        self._parent = parent
        self._ip_ver = ip_ver
        if self._ip_ver == 4:
            self._form = EditIPv4Form()
        else:
            self._form = EditIPv6Form()

        urwid.connect_signal(self._form.method.widget, 'select',
                             self._select_method)

        data = self._parent.controller.get_ip_config(self._ip_ver)
        method = data['method']
        self._form.method.widget.value = method
        if method == 'static':
            self._form.static_subform.widget.value = {'address': data['address'],
                                                      'gateway': data['gateway'],
                                                      'name_servers': ','.join(data['name_servers']),
                                                      'search_domains': ','.join(data['search_domains'])}
        self._select_method(None, method)

        urwid.connect_signal(self._form, 'submit', self.done)
        urwid.connect_signal(self._form, 'cancel', self.cancel)

        super().__init__('Edit IPv{} Configuration'.format(self._ip_ver),
                         [Pile(self._form.as_rows()), urwid.Text(''), self._form.buttons],
                         0, 0)

    def _select_method(self, sender, method: str):
        if method == 'static':
            self._form.static_subform.enabled = True
        else:
            self._form.static_subform.enabled = False
        self._form.static_subform.in_error = False
        self._form.validated()

    def done(self, sender):
        all_data = self._form.as_data()
        data = {'method': all_data['method']}
        data.update(all_data.get('static_subform', {}))
        self._parent.controller.set_ip_config(self._ip_ver, data)

    def cancel(self, sender=None):
        self._parent.remove_overlay()
