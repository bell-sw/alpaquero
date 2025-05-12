#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import logging

import urwid

from subiquitycore.view import BaseView
from subiquitycore.ui.form import (
    Form,
    SubForm,
    SubFormField,
    StringField,
    ChoiceField,
)

log = logging.getLogger('views.network_configure')


class IPv4ManualForm(SubForm):
    address = StringField('Address:', help='IP address in the CIDR form')
    gateway = StringField('Gateway:')
    name_servers = StringField('Name servers:', help='IP addresses, comma separated')
    search_domains = StringField('Search domains:', help='Domains, comma separated')


class ConfigurationForm(Form):
    cancel_label = 'Back'

    ipv4_method = ChoiceField('IPv4:', choices=['disabled', 'dhcp', 'manual'])
    ipv4_manual = SubFormField(IPv4ManualForm, '')
    ipv6_method = ChoiceField('IPv6:', choices=['disabled', 'manual'])
    ipv6_manual = SubFormField(IPv4ManualForm, '')


class NetworkConfigureView(BaseView):
    title = 'Network interface configuration'

    ok_label = 'Done'
    cancel_label = 'Back'

    def __init__(self, controller, iface_name: str):
        self.controller = controller
        self.excerpt = 'Configure {}'.format(iface_name)

        self._form = ConfigurationForm()

        urwid.connect_signal(self._form.ipv4_method.widget, 'select',
                             self._select_ipv4_method)
        urwid.connect_signal(self._form.ipv6_method.widget, 'select',
                             self._select_ipv6_method)
        self._form.ipv4_method.widget.index = 0
        self._form.ipv6_method.widget.index = 0

        urwid.connect_signal(self._form, 'submit', self.done)
        urwid.connect_signal(self._form, 'cancel', self.cancel)

        super().__init__(self._form.as_screen(focus_buttons=False, excerpt=self.excerpt))

    def _select_ipv4_method(self, sender, method: str):
        if method == 'manual':
            self._form.ipv4_manual.enabled = True
        else:
            self._form.ipv4_manual.enabled = False

    def _select_ipv6_method(self, sender, method: str):
        if method == 'manual':
            self._form.ipv6_manual.enabled = True
        else:
            self._form.ipv6_manual.enabled = False

    def done(self, sender):
        self.controller.done()

    def cancel(self, sender=None):
        self.controller.cancel()
