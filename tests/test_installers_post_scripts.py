#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import pytest

from alpaquero.installers.installer import InstallerException
from alpaquero.installers.post_scripts import PostScriptsInstaller
from .utils import new_installer, StubEventReceiver


def create_installer(config: dict) -> PostScriptsInstaller:
    return new_installer(PostScriptsInstaller, config=config)


def test_no_post_install():
    receiver = StubEventReceiver()
    installer = new_installer(PostScriptsInstaller, config={},
                              event_receiver=receiver)
    installer.post_apply()

    assert len(receiver.event_lines) == 0
    assert len(receiver.log_lines) == 0


def test_sh_script():
    receiver = StubEventReceiver()

    installer = new_installer(PostScriptsInstaller, config={'post_scripts': [
        {'interpreter': '/bin/sh',
         'chroot': False,
         'script': 'echo Hello\necho Shell'}
    ]}, event_receiver=receiver)
    installer.post_apply()

    assert receiver.log_lines[2] == 'Command output: Hello\nShell\n'


def test_python_script():
    receiver = StubEventReceiver()

    installer = new_installer(PostScriptsInstaller, config={'post_scripts': [
        {'interpreter': 'python3',
         'chroot': False,
         'script': "print('Hello')\nprint('Python')"}
    ]}, event_receiver=receiver)
    installer.post_apply()

    assert receiver.log_lines[2] == 'Command output: Hello\nPython\n'


def test_valid_format_wo_chroot():
    create_installer({'post_scripts': [
        {'interpreter': '/bin/sh',
         'script': 'echo hello'},
    ]})


def test_valid_format_w_chroot():
    create_installer({'post_scripts': [
        {'interpreter': '/bin/sh',
         'chroot': False,
         'script': 'echo hello'},
    ]})


def test_invalid_post_install_type():
    with pytest.raises(InstallerException):
        create_installer({'post_scripts': False})


def test_invalid_list_format():
    with pytest.raises(ValueError, match='elements must be of type'):
        create_installer({'post_scripts': [
            {'interpreter': '/bin/sh',
             'script': 'echo hello'},
            'INVALID FORMAT'
        ]})


def test_invalid_interpreter_format():
    with pytest.raises(ValueError, match='post_scripts/0'):
        create_installer({'post_scripts': [
            {'interpreter': 12,
             'script': 'echo hello'},
        ]})


def test_invalid_chroot_format():
    with pytest.raises(ValueError, match='post_scripts/0'):
        create_installer({'post_scripts': [
            {'interpreter': '/bin/sh',
             'chroot': 0,
             'script': 'echo hello'},
        ]})


def test_invalid_script_format():
    with pytest.raises(ValueError, match='post_scripts/0'):
        create_installer({'post_scripts': [
            {'interpreter': '/bin/sh',
             'script': []},
        ]})


def test_empty_interpreter():
    for value in [' ', '']:
        with pytest.raises(ValueError, match='post_scripts/0'):
            create_installer({'post_scripts': [
                {'interpreter': value,
                 'script': 'some content'},
            ]})


def test_empty_script():
    for value in [' ', '']:
        with pytest.raises(ValueError, match='post_scripts/0'):
            create_installer({'post_scripts': [
                {'interpreter': '/bin/sh',
                 'script': value},
            ]})
