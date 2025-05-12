#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import urwid

from subiquitycore.view import BaseView
from subiquitycore.ui.form import Form, StringField

from alpaquero.common.utils import validate_proxy_url, VALID_PROXY_URL_TEMPLATE


class ProxyForm(Form):
    ok_label = 'Next'
    cancel_label = 'Back'

    proxy_url = StringField('Proxy:',
                            help=VALID_PROXY_URL_TEMPLATE)

    def clean_proxy_url(self, value):
        if value:
            validate_proxy_url(value)


class ProxyView(BaseView):
    title = 'Proxy'
    excerpt = ('info_minor', (
        'If your system requires an HTTP proxy to connect to the Internet,'
        ' set it here.'))

    def __init__(self, controller, proxy: str):
        self._controller = controller

        self._form = ProxyForm()
        self._form.proxy_url.widget.value = proxy

        urwid.connect_signal(self._form, 'submit', self.done)
        urwid.connect_signal(self._form, 'cancel', self.cancel)

        super().__init__(self._form.as_screen(excerpt=self.excerpt,
                                              focus_buttons=True))

    def done(self, sender):
        self._controller.done(self._form.proxy_url.widget.value)

    def cancel(self, sender=None):
        self._controller.cancel()
