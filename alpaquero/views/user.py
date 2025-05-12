#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import re
from typing import Optional

from attrs import define
import urwid

from subiquitycore.view import BaseView
from subiquitycore.ui.form import (
    Form,
    StringField,
    PasswordField,
)

from alpaquero.models.user import USERNAME_REGEX, USERNAME_MAX_LEN, GECOS_INVALID_CHARACTERS


@define
class UserViewData:
    full_name: str
    user_name: str
    password: str


class UserForm(Form):
    ok_label = 'Next'
    cancel_label = 'Back'

    full_name = StringField('Full name:')
    user_name = StringField('User name:')

    password = PasswordField('Password:')
    confirm = PasswordField('Confirm:')

    def __init__(self, data: Optional[UserViewData]):
        super().__init__()
        if data is not None:
            self.full_name.value = data.full_name
            self.user_name.value = data.user_name
            self.password.value = data.password
            self.confirm.value = data.password

    def clean_full_name(self, value):
        if value:
            if set(value).intersection(set(GECOS_INVALID_CHARACTERS)):
                raise ValueError('Full name must not contain characters: {}'.format(
                    ','.join(f'\'{c}\'' for c in sorted(GECOS_INVALID_CHARACTERS))))
        return value

    def validate_user_name(self):
        user_name = self.user_name.value

        if len(user_name) < 1:
            return 'User name is not set'
        if len(user_name) > USERNAME_MAX_LEN:
            return f'User name must be <= {USERNAME_MAX_LEN} characters'
        if not re.match(USERNAME_REGEX, user_name):
            return f"User name must match regex '{USERNAME_REGEX}'"

    def validate_password(self):
        if len(self.password.value) < 1:
            return 'Password is not set'

    def validate_confirm(self):
        if self.password.value != self.confirm.value:
            return 'Confirm and Password fields do not match'


class UserView(BaseView):
    title = 'User'
    excerpt = ('info_minor', 'Create a user account. This account will have admin privileges.')

    def __init__(self, controller, data: Optional[UserViewData]):
        self._controller = controller

        self._form = UserForm(data)

        urwid.connect_signal(self._form, 'submit', self.done)
        urwid.connect_signal(self._form, 'cancel', self.cancel)

        super().__init__(self._form.as_screen(excerpt=self.excerpt,
                                              focus_buttons=False))

    def done(self, sender):
        data = UserViewData(full_name=self._form.full_name.value,
                            user_name=self._form.user_name.value,
                            password=self._form.password.value)
        self._controller.done(data)

    def cancel(self, sender=None):
        self._controller.cancel()
