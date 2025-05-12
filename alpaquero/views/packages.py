#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import urwid
from subiquitycore.view import BaseView
from subiquitycore.ui.form import (
    Form,
    SubForm,
    SubFormField,
    BooleanField,
    NO_HELP
)

from alpaquero.app.distro import DISTRO_NAME, DISTRO_JDK8, DISTRO_JDK11, DISTRO_JDK17, \
    DISTRO_JDK21, DISTRO_NIK23_17, DISTRO_NIK23_21, DISTRO_NIK24_22


class KernelForm(SubForm):
    extramods = BooleanField('Install firmware and extra modules',
                             help=('info_minor', (
                                 'This option installs components which may be required for '
                                 f'operating {DISTRO_NAME} on bare-metal machines.')))


class JavaForm(SubForm):
    jdk_8 = BooleanField(DISTRO_JDK8.description, help=NO_HELP)
    jdk_11 = BooleanField(DISTRO_JDK11.description, help=NO_HELP)
    jdk_17 = BooleanField(DISTRO_JDK17.description, help=NO_HELP)
    jdk_21 = BooleanField(DISTRO_JDK21.description, help=NO_HELP)
    nik_23_17 = BooleanField(DISTRO_NIK23_17.description, help=NO_HELP)
    nik_23_21 = BooleanField(DISTRO_NIK23_21.description, help=NO_HELP)
    nik_24_22 = BooleanField(DISTRO_NIK24_22.description, help=NO_HELP)


class LibcForm(SubForm):
    perf = BooleanField('Install musl-perf with CPU features detection and optimized asm functions',
                        help=NO_HELP)


class OtherForm(SubForm):
    ssh_server = BooleanField('Enable SSH access', help=NO_HELP)
    coreutils = BooleanField('Install GNU Core Utilities',
                             help=('info_minor', (
                                 'This option installs basic file, shell and text manipulation utilities '
                                 'from the GNU coreutils project on top of busybox (which is always '
                                 'installed by default).')))


class PackagesForm(Form):
    ok_label = 'Next'
    cancel_label = 'Back'
    kernel = SubFormField(KernelForm, 'Linux kernel')
    jdk = SubFormField(JavaForm, 'Java')
    libc = SubFormField(LibcForm, 'libc')
    other = SubFormField(OtherForm, 'Other components', help=NO_HELP)


class PackagesView(BaseView):
    title = 'Packages'
    excerpt = ('info_minor', 'Select additional packages to install.')

    def __init__(self, controller, data, is_musl):
        self._controller = controller
        self._form = PackagesForm()
        self._form.kernel.widget.value = data.get('kernel')

        for k, f in [('kernel', self._form.kernel),
                     ('jdk', self._form.jdk),
                     ('libc', self._form.libc),
                     ('other', self._form.other)]:
            if k in data:
                f.widget.value = data.get(k)

        if not is_musl:
            self._form.libc.enabled = False

        urwid.connect_signal(self._form, 'submit', self.done)
        urwid.connect_signal(self._form, 'cancel', self.cancel)
        super().__init__(self._form.as_screen(excerpt=self.excerpt,
                                              focus_buttons=True))

    def done(self, sender):
        self._controller.done({
            'kernel': self._form.kernel.widget.value,
            'jdk': self._form.jdk.widget.value,
            'libc': self._form.libc.widget.value,
            'other': self._form.other.widget.value,
            })

    def cancel(self, sender=None):
        self._controller.cancel()
