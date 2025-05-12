#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

import attrs
import urwid

from subiquitycore.view import BaseView
from subiquitycore.ui.form import Form, SubForm, BooleanField, ChoiceField, PasswordField, SubFormField
from subiquitycore.ui.selector import Option

if TYPE_CHECKING:
    from alpaquero.controllers.storage import StorageController, Disk


@attrs.define
class StorageViewData:
    use_lvm: bool
    file_system: str
    selected_disk: Optional[Disk] = None
    crypto_passphrase: Optional[str] = None


class PassphraseForm(SubForm):
    passphrase = PasswordField('Passphrase:')
    confirm = PasswordField('Confirm:')


class StorageForm(Form):
    ok_label = 'Next'
    cancel_label = 'Back'

    disk = ChoiceField('Disk:', choices=['dummy'])
    file_system = ChoiceField('File system:', choices=['xfs', 'ext4'])
    use_lvm = BooleanField('Set up this disk as an LVM group')
    encrypt = BooleanField('Enable encryption with LUKS')
    encrypt_subform = SubFormField(PassphraseForm, '')

    def validate_encrypt_subform(self):
        if not self.encrypt.value:
            return
        data = self.encrypt_subform.value
        if len(data['passphrase']) < 1:
            return 'Passphrase is not set'
        if data['passphrase'] != data['confirm']:
            return 'Confirm and Passphrase fields do not match'


class StorageView(BaseView):
    title = 'Installation Destination'
    excerpt = ('info_minor', (
        'Select a disk for installation. All existing data on this disk will be lost.'))

    def __init__(self, controller: StorageController,
                 available_disks: list[Disk],
                 data: StorageViewData):
        self._controller = controller
        self._available_disks = available_disks
        self._selected_disk = data.selected_disk

        self._form = StorageForm()
        self._form.use_lvm.value = data.use_lvm
        self._init_disks_list()

        self._form.file_system.value = data.file_system

        urwid.connect_signal(self._form.encrypt.widget, 'change', self._encrypt_change)
        if data.crypto_passphrase:
            self._form.encrypt.value = True
            self._form.encrypt_subform.value = {'passphrase': data.crypto_passphrase,
                                                'confirm': data.crypto_passphrase}
        else:
            self._form.encrypt.value = False
        urwid.emit_signal(self._form.encrypt.widget, 'change', None, self._form.encrypt.value)

        urwid.connect_signal(self._form, 'submit', self.done)
        urwid.connect_signal(self._form, 'cancel', self.cancel)

        super().__init__(self._form.as_screen(excerpt=self.excerpt,
                                              focus_buttons=True))

    def _encrypt_change(self, sender, value):
        self._form.encrypt_subform.enabled = value
        self._form.encrypt_subform.in_error = False
        self._form.validated()

    @staticmethod
    def _disk_label(disk: Disk) -> str:
        model = ''
        if disk.model:
            serial = ''
            if disk.serial:
                serial = ', {}'.format(disk.serial)
            model = ' ({}{})'.format(disk.model, serial)

        size = disk.size / (1024 * 1024 * 1024)

        return '{}{} {:.2f} GB'.format(disk.path, model, size)

    def _init_disks_list(self):
        disk_opts = []
        dev_to_select = None
        for dev in self._available_disks:
            disk_opts.append(Option((self._disk_label(dev), True, dev)))
            if dev.path == self._selected_disk:
                dev_to_select = dev
        self._form.disk.widget.options = disk_opts
        if not dev_to_select:
            dev_to_select = disk_opts[0].value
        self._form.disk.widget.value = dev_to_select

    def done(self, sender):
        passphrase = None
        if self._form.encrypt.value:
            passphrase = self._form.encrypt_subform.value['passphrase']
        data = StorageViewData(selected_disk=self._form.disk.value,
                               file_system=self._form.file_system.value,
                               use_lvm=self._form.use_lvm.value,
                               crypto_passphrase=passphrase)
        self._controller.done(data)

    def cancel(self, sender=None):
        self._controller.cancel()
