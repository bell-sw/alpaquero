#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import attrs

from .installer import Installer
from .utils import read_list

# Optional
#
# post_scripts:
#   - interpreter: /bin/sh
#     chroot: true # Optional, true by default
#     script: cat /etc/passwd
#
# The script content wil be passed to the standard input of the interpreter.
#


def validate_empty(value: str):
    if not value.strip():
        raise ValueError(f"'{value}' is an empty string")


@attrs.define
class ScriptDescr:
    interpreter: str = attrs.field(validator=attrs.validators.instance_of(str))
    script: str = attrs.field(validator=attrs.validators.instance_of(str))
    chroot: bool = attrs.field(default=True, validator=attrs.validators.instance_of(bool))

    @interpreter.validator
    def check_interpreter(self, attribute, value):
        validate_empty(value)

    @script.validator
    def check_script(self, attribute, value):
        validate_empty(value)


class PostScriptsInstaller(Installer):
    def __init__(self, target_root: str, config: dict, event_receiver):
        yaml_tag = 'post_scripts'
        super().__init__(name=yaml_tag, config=config,
                         event_receiver=event_receiver,
                         data_type=list, data_is_optional=True,
                         target_root=target_root)

        self._scripts = []
        items = read_list(data=config, key=yaml_tag, item_type=dict,
                          error_label=f'{yaml_tag}')
        for (idx, item) in enumerate(items):
            try:
                script = ScriptDescr(**item)
            except (ValueError, TypeError):
                raise ValueError(f"Error in parsing '{yaml_tag}/{idx}'")
            self._scripts.append(script)

    def apply(self):
        pass

    def post_apply(self):
        if len(self._scripts) == 0:
            return

        for script in self._scripts:
            args = script.interpreter.split()
            script_content = bytes(script.script, encoding='utf-8')
            self._event_receiver.add_log_line("Executing post install script. Interpreter: '{}', chroot: {}, script: '{}'".format(
                script.interpreter, script.chroot, script.script
            ))
            if script.chroot:
                self.run_in_chroot(args=args, input=script_content)
            else:
                self.run(args=args, input=script_content)
