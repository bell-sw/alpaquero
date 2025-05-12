#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from typing import Optional
import crypt
import logging

import yaml

from alpaquero.models.user import UserModel
from alpaquero.views.user import UserView, UserViewData
from .controller import Controller

log = logging.getLogger('controllers.users')


class UserController(Controller):
    def __init__(self, app):
        super().__init__(app)
        self._model = None

    def make_ui(self):
        data = None
        if self._model is not None:
            data = UserViewData(full_name=self._model.gecos,
                                user_name=self._model.name,
                                password=self._model.password)

        return UserView(self, data)

    def done(self, data: Optional[UserViewData]):
        new_model = None
        if data is not None:
            try:
                new_model = UserModel(gecos=data.full_name,
                                      name=data.user_name,
                                      is_admin=True,
                                      password=data.password)
            except (ValueError, TypeError) as exc:
                self._app.show_error_message(str(exc))
                return

        self._model = new_model
        log.debug('User = {}'.format(self._model))
        self._app.next_screen()

    def cancel(self):
        self._app.prev_screen()

    def to_yaml(self) -> str:
        user_data = {'name': self._model.name,
                     'password': crypt.crypt(self._model.password),
                     'gecos': self._model.gecos,
                     'is_admin': self._model.is_admin}
        yaml_data = yaml.dump({'users': [user_data]})
        log.debug('export to yaml: {}'.format(yaml_data))
        return yaml_data
