#  SPDX-FileCopyrightText: 2024 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from collections import OrderedDict

import urwid

from subiquitycore.view import BaseView
from subiquitycore.ui.form import Form, BooleanField


class SerialConsoleView(BaseView):
    title = "Serial console"
    excerpt = ("info_minor", (
        "The installed system will enable login on the graphical console.\n\n"
        "In addition to that login will also be enabled on the selected serial consoles."))

    def __init__(self, controller):
        self._controller = controller

        form_fields = OrderedDict({
            "ok_label": "Next",
            "cancel_label": "Back",
        })
        for tty in sorted(self._controller.tty_state.keys()):
            field = BooleanField(tty)
            if tty == self._controller.active_tty:
                field.help = ("info_minor", "(currently active)")
            form_fields[tty] = field

        SerialConsoleForm = type("SerialConsoleForm", (Form,), form_fields)
        self._form = SerialConsoleForm()
        for tty, value in self._controller.tty_state.items():
            getattr(self._form, tty).widget.value = value

        urwid.connect_signal(self._form, "submit", self.done)
        urwid.connect_signal(self._form, "cancel", self.cancel)

        super().__init__(self._form.as_screen(excerpt=self.excerpt,
                                              focus_buttons=True))

    def done(self, sender):
        self._controller.done(tty_state=self._form.as_data())

    def cancel(self, sender=None):
        self._controller.cancel()
