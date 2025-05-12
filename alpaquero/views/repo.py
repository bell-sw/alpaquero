#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import urwid

from subiquitycore.view import BaseView
from subiquitycore.ui.form import (
    Form,
    SubForm,
    URLField,
    ReadOnlyField,
    ChoiceField,
    SubFormField,
    NO_HELP
)


class UrlsForm(SubForm):
    field0 = ReadOnlyField('', help=NO_HELP)
    field1 = ReadOnlyField('')


class RepoForm(Form):
    ok_label = 'Next'
    cancel_label = 'Back'

    libc_type = ChoiceField('libc type:', choices=['musl', 'glibc'])
    repo_base_url = URLField('Base URL:')
    repo_fields = SubFormField(UrlsForm, 'Repositories:')


class RepoView(BaseView):
    title = 'Installation Source'
    excerpt = ('info_minor', (
        'Specify the URL of the repository server that '
        'will be used to install the packages.'))

    def __init__(self, controller, repo_base_url: str, libc_type: str,
                 iso_mode: bool):
        self._controller = controller

        self._form = RepoForm()
        self._form.repo_base_url.widget.value = repo_base_url
        self._form.libc_type.widget.value = libc_type
        self._libc = libc_type
        self._url = repo_base_url
        self._set_repos_text()

        urwid.connect_signal(self._form, 'submit', self.done)
        urwid.connect_signal(self._form, 'cancel', self.cancel)
        urwid.connect_signal(self._form.repo_base_url.widget, 'change',
                             self._update_repos_text_url)
        urwid.connect_signal(self._form.libc_type.widget, 'select',
                             self._update_repos_text_libc)

        # We prohibit cross-libc installations on ISOs.
        if iso_mode:
            self._form.libc_type.enabled = False

        super().__init__(self._form.as_screen(excerpt=self.excerpt,
                                              focus_buttons=True))

    def done(self, sender):
        self._controller.done(self._form.repo_base_url.widget.value,
                              self._form.libc_type.widget.value)

    def cancel(self, sender=None):
        self._controller.cancel()

    def _set_repos_text(self):
        d = {}
        for r, k in zip(self._controller.get_repos(self._url, self._libc), ['field0', 'field1']):
            d[k] = r
        self._form.repo_fields.widget.value = d

    def _update_repos_text_url(self, sender, url):
        self._url = url
        self._set_repos_text()

    def _update_repos_text_libc(self, sender, libc):
        self._libc = libc
        self._set_repos_text()
