#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
from typing import TYPE_CHECKING

import urwid

from subiquitycore.ui.form import Form, StringField, PasswordField
from subiquitycore.ui.container import Pile
from subiquitycore.ui.stretchy import Stretchy

from alpaquero.nmanager.wifi_config import validate_wifi_ssid, validate_wifi_psk

if TYPE_CHECKING:
    from .network import NetworkView


class WIFIForm(Form):
    ok_label = 'Save'

    ssid = StringField('Network SSID:')
    psk = PasswordField('WPA2 passphrase:')

    def clean_ssid(self, value: str) -> str:
        validate_wifi_ssid(value)
        return value.strip()

    def clean_psk(self, value: str) -> str:
        validate_wifi_psk(value)
        return value


class EditWIFIStretchy(Stretchy):
    def __init__(self, parent: NetworkView):
        self._parent = parent
        self._form = WIFIForm()

        data = self._parent.controller.get_wifi_config()
        if data:
            self._form.ssid.widget.value = data['ssid']
            self._form.psk.widget.value = data['psk']

        urwid.connect_signal(self._form, 'submit', self.done)
        urwid.connect_signal(self._form, 'cancel', self.cancel)

        super().__init__('Edit WIFI configuration',
                         [Pile(self._form.as_rows()), urwid.Text(''), self._form.buttons],
                         0, 0)

    def done(self, sender):
        self._parent.controller.set_wifi_config(self._form.as_data())

    def cancel(self, sender=None):
        self._parent.remove_overlay()
