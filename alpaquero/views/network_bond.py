#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import urwid

from subiquitycore.ui.form import Form, StringField, ChoiceField
from subiquitycore.ui.container import Pile
from subiquitycore.ui.stretchy import Stretchy
from subiquitycore.ui.views.network_configure_manual_interface import MultiNetdevField
from subiquitycore.ui.selector import Option

from alpaquero.nmanager.bond_config import BOND_MODES, hash_policies_for_bond_mode
from alpaquero.nmanager.manager import NetworkManager

if TYPE_CHECKING:
    from .network import NetworkView

log = logging.getLogger('views.network_bond')


class BondForm(Form):
    ok_label = 'Create'

    name = StringField('Name:')
    ifaces = MultiNetdevField('Interfaces:')
    mode = ChoiceField('Bond mode:', choices=BOND_MODES)
    hash_policy = ChoiceField('XMIT hash policy:', choices=['dummy'])

    def __init__(self, candidate_ifaces: list[str]):
        # This name is used by MultiNetdevField
        self.candidate_netdevs = candidate_ifaces[:]
        super().__init__()

        self._select_mode(None, BOND_MODES[0])

        urwid.connect_signal(self.mode.widget, 'select', self._select_mode)

    def _select_mode(self, sender, mode: str, hash_policy: Optional[str] = None):
        policies = hash_policies_for_bond_mode(mode)
        pol_opts = []
        if policies:
            for policy in policies:
                pol_opts.append(Option((policy, True, policy)))
            self.hash_policy.enabled = True
        else:
            pol_opts.append(Option((' ', True, ' ')))
            self.hash_policy.enabled = False

        self.hash_policy.widget.options = pol_opts

        if hash_policy:
            self.hash_policy.widget.value = hash_policy
        else:
            self.hash_policy.widget.index = 0

    def clean_name(self, value: str) -> str:
        if (len(value) < 2) or (len(value) > 16):
            raise ValueError('Name must be from 2 to 16 characters')
        if not NetworkManager.is_valid_iface_name(value):
            raise ValueError('Invalid name')
        return value


class CreateBondStretchy(Stretchy):
    def __init__(self, parent: NetworkView, candidates: set[str]):
        self._parent = parent

        candidates = sorted(self._parent.controller.get_bond_candidates())
        self._form = BondForm(candidate_ifaces=candidates)

        urwid.connect_signal(self._form, 'submit', self.done)
        urwid.connect_signal(self._form, 'cancel', self.cancel)

        super().__init__('Create bond',
                         [Pile(self._form.as_rows()), urwid.Text(''), self._form.buttons],
                         0, 0)

    def done(self, sender):
        data = self._form.as_data()
        hash_policy = data.get('hash_policy', None)
        log.warning('data: {}'.format(data))
        self._parent.controller.add_bond_iface(name=data['name'], members=data['ifaces'],
                                               mode=data['mode'], hash_policy=hash_policy)

    def cancel(self, sender=None):
        self._parent.remove_overlay()
