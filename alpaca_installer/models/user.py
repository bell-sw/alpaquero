#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from attrs import define, field, validators

# From 'man 8 useradd' in Ubuntu
USERNAME_REGEX = r'^[a-z_][a-z0-9_-]*[$]?$'
USERNAME_MAX_LEN = 32

def _password_not_empty(instance, attribute, value):
    if not value:
        raise ValueError('password is empty')


@define
class UserModel:
    gecos: str = field(validator=validators.optional(validators.instance_of(str)))
    name: str = field(validator=[validators.instance_of(str),
                                 validators.max_len(USERNAME_MAX_LEN),
                                 validators.matches_re(USERNAME_REGEX)])
    is_admin: bool = field(validator=validators.instance_of(bool))
    password: str = field(validator=[validators.instance_of(str),
                                     _password_not_empty])
