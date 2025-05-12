#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import datetime

from alpaquero.common.utils import write_file
from alpaquero.models.user import UserModel
from .installer import Installer, InstallerException
from .utils import read_list

# Optional
#
# The root user is always disabled.
#
# users:
#   - name: user1
#     password: <password hash> # for example, with crypt.crypt()
#     gecos: 'gecos for user1' # optional
#     is_admin: false
#   - name: admin
#     password: <password hash>
#     is_admin: true
#


def read_user_from_dict(data: dict) -> UserModel:
    name = data.get('name', None)
    password_hash = data.get('password', None)
    gecos = data.get('gecos', None)
    is_admin = data.get('is_admin', False)

    user = UserModel(name=name, gecos=gecos, is_admin=is_admin,
                     password=password_hash)

    # As it's a separator in /etc/shadow
    if ':' in user.password:
        raise ValueError("':' is prohibited in 'password'")

    return user


def update_user_hash(etc_shadow: str, user: str, password_hash: str):
    with open(etc_shadow, 'r') as file:
        lines = file.readlines()

    found_user = False
    for i, line in enumerate(lines):
        tokens = line.split(':')
        if tokens[0] != user:
            continue

        # Encrypted password
        tokens[1] = password_hash
        # Date of last password change (number of days since the Unix epoch)
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
        tokens[2] = str((now - epoch).days)
        lines[i] = ':'.join(tokens)
        found_user = True

    if not found_user:
        raise RuntimeError("No user '{}' found in '{}'".format(user, etc_shadow))

    write_file(etc_shadow, 'w', data=''.join(lines))


class UsersInstaller(Installer):
    def __init__(self, target_root: str, config: dict, event_receiver):
        yaml_tag = 'users'
        super().__init__(name=yaml_tag, target_root=target_root,
                         event_receiver=event_receiver,
                         data_is_optional=True,
                         data_type=list, config=config)

        self._users: list[UserModel] = []

        for item in read_list(config, key=yaml_tag, item_type=dict, error_label=yaml_tag):
            try:
                user = read_user_from_dict(item)
            except (TypeError, ValueError) as exc:
                raise InstallerException(str(exc)) from None
            if user.name == 'root':
                raise InstallerException('No root user must be defined')
            self._users.append(user)

        # It would be strange to have a system without sudo
        self.add_package('sudo')

    def apply(self):
        write_file(self.abs_target_path('/etc/sudoers.d/00-wheel'), 'w',
                   data='%wheel ALL=(ALL) ALL\n')

        etc_shadow = self.abs_target_path('/etc/shadow')

        # Disable the root user
        update_user_hash(etc_shadow=etc_shadow, user='root',
                         password_hash='!')

        if not self._users:
            return

        self._event_receiver.start_event('Adding users')

        for user in self._users:
            args = ['adduser', '-D']
            if user.gecos:
                args.extend(['-g', user.gecos])
            # don't let host's $SHELL affect the shell choice
            # TODO: provide ui and yaml key for this
            args.extend(['-s', '/bin/sh'])
            args.append(user.name)
            self.run_in_chroot(args=args)

            update_user_hash(etc_shadow=etc_shadow, user=user.name,
                             password_hash=user.password)

            if user.is_admin:
                self.run_in_chroot(args=['addgroup', user.name, 'wheel'])
