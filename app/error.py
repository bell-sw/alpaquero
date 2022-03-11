import urwid

from subiquitycore.ui.stretchy import Stretchy
from subiquitycore.ui.buttons import ok_btn
from subiquitycore.ui.utils import button_pile


class ErrorMsgStretchy(Stretchy):
    def __init__(self, app, msg: str, title: str = 'Error'):
        self._app = app
        _ok_btn = ok_btn('Close', on_press=self._close)
        super().__init__(title, [urwid.Text(msg), button_pile([_ok_btn])], 0, 1)

    def _close(self, sender):
        self._app.ui.body.remove_overlay(self)
