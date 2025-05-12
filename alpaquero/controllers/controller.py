#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alpaquero.app.application import Application


class Controller:
    def __init__(self, app: Application):
        self._app = app

    def to_yaml(self) -> str:
        return ''
