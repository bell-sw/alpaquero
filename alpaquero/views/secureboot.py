#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import urwid
from subiquitycore.view import BaseView
from subiquitycore.ui.form import (
    Form,
    BooleanField,
    ReadOnlyField,
)

from alpaquero.app.distro import DISTRO_NAME


class SecureBootForm(Form):
    ok_label = 'Next'
    cancel_label = 'Back'
    install_shim = BooleanField('Install Secure Boot required packages to sign with own keys')


class SecureBootView(BaseView):
    title = 'Secure Boot'
    excerpt = ('info_minor', (
        f'{DISTRO_NAME} provides pre-bootloader shim with a built-in certificate, '
        'signed MOKManager utility, grub and kernel (automatically locked down if '
        'Secure Boot is enabled).\n\n'
        'The currently provided shim EFI image is not yet signed by Microsoft, so '
        'it cannot be loaded with Secure Boot enabled using Microsoft certificates. '
        'For it to work, the shim must be signed with your own trusted Secure Boot '
        'key from UEFI Signature Database (db) or the shim hash added there.\n\n'
        'If the option is selected, shim, signed grub, sbsigntool, efitools and '
        'mokutil packages will also be installed.'))

    def __init__(self, controller, install_shim):
        self._controller = controller
        self._form = SecureBootForm()
        self._form.install_shim.widget.value = install_shim

        urwid.connect_signal(self._form, 'submit', self.done)
        urwid.connect_signal(self._form, 'cancel', self.cancel)
        super().__init__(self._form.as_screen(excerpt=self.excerpt,
                                              focus_buttons=True))

    def done(self, sender):
        self._controller.done(self._form.install_shim.widget.value)

    def cancel(self, sender=None):
        self._controller.cancel()
