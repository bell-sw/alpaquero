#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import attrs


def validate_wifi_ssid(ssid: str):
    if (len(ssid) < 2) or (len(ssid) > 32):
        raise ValueError('SSID must be from 2 to 32 characters')

    # ifupdown-ng limitation
    if '#' in ssid:
        raise ValueError('SSID must not contain #')


def validate_wifi_psk(psk: str):
    # wpa_passphrase requirement
    if (len(psk) < 8) or (len(psk) > 63):
        raise ValueError('PSK (passphrase) must be from 8 to 63 characters')

    # ifupdown-ng limitation
    if '#' in psk:
        raise ValueError('PSK (passphrase) must not contain #')


@attrs.define
class WIFIConfig:
    ssid: str = attrs.field(validator=attrs.validators.instance_of(str))
    psk: str = attrs.field(validator=attrs.validators.instance_of(str))

    @ssid.validator
    def check_ssid(self, attribute, value):
        validate_wifi_ssid(value)

    @psk.validator
    def check_psk(self, attribute, value):
        validate_wifi_psk(value)
