#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

import urwid

from subiquitycore.ui.buttons import done_btn
from subiquitycore.ui.container import ListBox, Pile
from subiquitycore.ui.form import Form, ChoiceField, StringField
from subiquitycore.ui.utils import screen
from subiquitycore.ui.selector import Option
from subiquitycore.ui.table import ColSpec, TablePile, TableRow
from subiquitycore.view import BaseView

from .network_vlan import AddVlanStretchy
from .network_edit import EditIPStretchy
from .network_wifi import EditWIFIStretchy
from .network_bond import CreateBondStretchy
from alpaquero.nmanager.ip_config import is_valid_hostname
from alpaquero.common.utils import button_width_for_label

if TYPE_CHECKING:
    from alpaquero.controllers.network import NetworkController


class NetworkForm(Form):
    ok_label = 'Next'
    cancel_label = 'Back'

    hostname = StringField('Hostname:')
    interface = ChoiceField('Interface:', choices=['dummy'])

    def clean_hostname(self, value):
        if not is_valid_hostname(value):
            raise ValueError("Invalid hostname: '{}'".format(value))
        return value


class NetworkView(BaseView):
    title = 'Network'
    excerpt = ('info_minor', (
        'Enter the hostname of the system and select a network interface connected to the Internet.'))

    def __init__(self, controller: NetworkController):
        self.controller = controller
        self._selected_iface = self.controller.get_selected_iface()

        self._network_form = NetworkForm(initial={'hostname': self.controller.get_hostname()})

        self._bond_btn_label = 'Create bond interface'
        self._bond_btn = done_btn(self._bond_btn_label, on_press=self._add_bond)
        self._vlan_btn_label = 'Add VLAN'
        self._vlan_btn = done_btn(self._vlan_btn_label, on_press=self._add_vlan)
        self._delete_btn_label = 'Delete'
        self._delete_btn = done_btn(self._delete_btn_label, on_press=self._del_iface)

        self._actions_placeholder = urwid.WidgetPlaceholder(urwid.Text(''))
        self._wifi_placeholder = urwid.WidgetPlaceholder(urwid.Text(''))

        self._ipv4_status = urwid.Text('IPv4 status')
        self._ipv6_status = urwid.Text('IPv6 status')
        self.update_ip_statuses()
        edit_ipv4_btn = done_btn('Edit', on_press=self._edit_ipv4)
        edit_ipv6_btn = done_btn('Edit', on_press=self._edit_ipv6)

        self._wifi_status = urwid.Text('WIFI status')
        edit_wifi_btn = done_btn('Edit', on_press=self._edit_wifi)
        self._wifi_table = TablePile([
            TableRow([self._wifi_status, edit_wifi_btn])
        ], {
            0: ColSpec(min_width=46),
            1: ColSpec()
        })

        urwid.connect_signal(self._network_form.interface.widget, 'select',
                             self._iface_selected)

        table = TablePile([
            TableRow([urwid.Text('IPv4:'), self._ipv4_status, edit_ipv4_btn]),
            TableRow([urwid.Text('IPv6:'), self._ipv6_status, edit_ipv6_btn]),
        ], {
            0: ColSpec(),
            1: ColSpec(min_width=40),
            2: ColSpec()
        })

        hostname_rows = self._network_form.as_rows()
        self._pile = Pile(hostname_rows +
                          [self._actions_placeholder,
                           urwid.Text(''),
                           urwid.Padding(self._bond_btn,
                                         width=button_width_for_label(self._bond_btn_label), align='left'),
                           urwid.Text(''),
                           self._wifi_placeholder,
                           urwid.Text(''),
                           urwid.Text('IP address configuration:'),
                           urwid.Text(''),
                           table])
        # Adjust it if any widgets above the interface selector are added/removed
        self._iface_selector_pos = len(hostname_rows) - 1

        self.update_interfaces_list(iface_to_select=self._selected_iface)
        self.update_wifi_status()

        urwid.connect_signal(self._network_form, 'submit', self.done)
        urwid.connect_signal(self._network_form, 'cancel', self.cancel)

        super().__init__(screen(ListBox([self._pile]), excerpt=self.excerpt,
                                buttons=self._network_form.buttons, focus_buttons=True))

    def _reset_focus(self):
        self._pile.focus_position = self._iface_selector_pos

    def _iface_selected(self, sender, value):
        self._selected_iface = value
        iface_info = self.controller.get_iface_info(value)
        widget = urwid.Text('')
        wifi_widget = urwid.Text('')
        if iface_info.type == 'ethernet':
            widget = urwid.Padding(self._vlan_btn,
                                   width=button_width_for_label(self._vlan_btn_label), align='left')
        elif iface_info.type == 'vlan':
            widget = urwid.Padding(self._delete_btn,
                                   width=button_width_for_label(self._delete_btn_label), align='left')
        elif iface_info.type == 'wifi':
            wifi_widget = Pile([urwid.Text('Wireless configuration:'),
                                urwid.Text(''),
                                self._wifi_table])
        elif iface_info.type == 'bond':
            widget = urwid.Padding(urwid.Columns([self._vlan_btn, self._delete_btn]),
                                   width=28, align='left')
        self._actions_placeholder.original_widget = widget
        self._wifi_placeholder.original_widget = wifi_widget
        # In case both the placeholders are Text widgets, we won't be able
        # to set focus on either of them.
        self._reset_focus()

    def _add_vlan(self, button):
        self.show_stretchy_overlay(AddVlanStretchy(self, self._selected_iface))

    def _add_bond(self, button):
        candidates = self.controller.get_bond_candidates()
        if not candidates:
            self.controller._app.show_error_message('No available interfaces.')
        else:
            self.show_stretchy_overlay(CreateBondStretchy(self, candidates=candidates))

    def _del_iface(self, button):
        self.controller.del_iface(self._selected_iface)

    def _edit_ipv4(self, button):
        self.show_stretchy_overlay(EditIPStretchy(self, 4))

    def _edit_ipv6(self, button):
        self.show_stretchy_overlay(EditIPStretchy(self, 6))

    def _edit_wifi(self, button):
        self.show_stretchy_overlay(EditWIFIStretchy(self))

    def _iface_label(self, name):
        info = self.controller.get_iface_info(name)
        if info.type in ('ethernet', 'wifi'):
            label = '{} / {} / {} / {}'.format(
                info.name, info.mac_address, info.vendor, info.model
            )
        elif info.type == 'vlan':
            label = '{} / VLAN {} on interface {}'.format(
                info.name, info.vlan_id, info.base_iface
            )
        elif info.type == 'bond':
            mode_policy = info.bond_mode
            if info.bond_hash_policy:
                mode_policy = '{} {}'.format(info.bond_mode, info.bond_hash_policy)
            label = '{} / {} bonding on {}'.format(
                info.name, mode_policy, ','.join(sorted(info.bond_members))
            )
        else:
            label = 'Unknown interface type'
        return label

    def update_interfaces_list(self, iface_to_select: Optional[str] = None):
        iface_opts = []
        for iface in sorted(self.controller.get_available_ifaces()):
            iface_opts.append(Option((self._iface_label(iface), True, iface)))
        self._network_form.interface.widget.options = iface_opts

        if not iface_to_select:
            iface_to_select = iface_opts[0].value

        self._network_form.interface.widget.value = iface_to_select
        urwid.emit_signal(self._network_form.interface.widget, 'select', None,
                          iface_to_select)

    def update_ip_statuses(self):
        def _to_status(data: dict[str, str]):
            if data['method'] == 'dhcp':
                return 'DHCP'
            elif data['method'] == 'disabled':
                return 'Disabled'
            elif data['method'] == 'static':
                return 'Static {}'.format(data['address'])
            else:
                raise ValueError('Unsupported IP method: {}'.format(data['method']))

        self._ipv4_status.set_text(_to_status(self.controller.get_ip_config(4)))
        self._ipv6_status.set_text(_to_status(self.controller.get_ip_config(6)))

    def update_wifi_status(self):
        data = self.controller.get_wifi_config()
        if data:
            text = 'SSID: {}'.format(data['ssid'])
        else:
            text = 'No SSID configured'
        self._wifi_status.set_text(text)

    def done(self, sender):
        self.controller.set_hostname(self._network_form.hostname.value)
        self.controller.select_iface(self._selected_iface)
        self.controller.done()

    def cancel(self, sender=None):
        self.controller.cancel()
