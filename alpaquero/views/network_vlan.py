#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
from typing import TYPE_CHECKING

import urwid

from subiquitycore.ui.form import Form, StringField
from subiquitycore.ui.container import Pile
from subiquitycore.ui.stretchy import Stretchy

if TYPE_CHECKING:
    from .network import NetworkView


class VlanForm(Form):
    ok_label = 'Add'
    cancel_label = 'Cancel'

    vlan_id = StringField('VLAN ID:')

    def clean_vlan_id(self, value):
        try:
            vlanid = int(value)
        except ValueError:
            vlanid = None
        if (vlanid is None) or (vlanid < 1) or (vlanid > 4095):
            raise ValueError('VLAN ID must be between 1 an 4095')
        return vlanid


class AddVlanStretchy(Stretchy):
    def __init__(self, parent: NetworkView, iface_name):
        self._parent = parent
        self._iface_name = iface_name
        self._form = VlanForm()

        urwid.connect_signal(self._form, 'submit', self.done)
        urwid.connect_signal(self._form, 'cancel', self.cancel)

        super().__init__('Add a VLAN tag on {}'.format(self._iface_name),
                         [Pile(self._form.as_rows()), urwid.Text(''), self._form.buttons],
                         0, 0)

    def done(self, sender):
        data = self._form.as_data()
        self._parent.controller.add_vlan_iface(self._iface_name, int(data['vlan_id']))

    def cancel(self, sender=None):
        self._parent.remove_overlay()
