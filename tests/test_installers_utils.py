#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import pytest

from alpaquero.installers.utils import (
    read_key_or_fail, str_size_to_bytes,
    validate_types_of_elements, read_list)


def test_read_key_or_fail_error_label():
    key = 'some_key'
    data = {key: 'some_value'}

    with pytest.raises(ValueError, match=fr"(?i)'{key}' must be of type"):
        read_key_or_fail(data, key=key, value_type=dict)

    error_label = 'some_label'
    with pytest.raises(ValueError, match=fr"(?i)'{error_label}' must be of type"):
        read_key_or_fail(data, key=key, value_type=dict, error_label=error_label)


def test_read_key_or_fail():
    data = {'key1': 'value1'}
    assert read_key_or_fail(data, key='key1', value_type=str) == 'value1'
    assert read_key_or_fail(data, key='key2', value_type=list) == []


def test_read_list():
    error_label = 'some label'
    with pytest.raises(ValueError, match=fr"'{error_label}'"):
        read_list({'key': 'value'}, key='key', item_type=int, error_label=error_label)

    assert read_list({'lst': [1, 2, 3]}, key='lst', item_type=int,
                     error_label=error_label) == [1, 2, 3]
    assert read_list({}, key='key', item_type=str,
                     error_label=error_label) == []


def test_validate_types_of_elements():
    data = [1, 2, 'three']
    error_label = 'some_error_label'
    with pytest.raises(ValueError, match=fr"(?i)All '{error_label}' elements"):
        validate_types_of_elements(data, item_type=int, error_label=error_label)

    validate_types_of_elements(['one', 'two'], item_type=str, error_label=error_label)


def test_str_size_to_bytes_invalid_format():
    for value in [' 8 ', '1Z', '-2K', '0.5G', '+4K', '-2M', '-8G', '1.2', 'G']:
        with pytest.raises(ValueError, match=r'(?i)invalid size format'):
            str_size_to_bytes(value)


def test_str_size_to_bytes():
    assert str_size_to_bytes('0') == 0
    assert str_size_to_bytes('00') == 0
    assert str_size_to_bytes('0K') == 0
    assert str_size_to_bytes('0M') == 0
    assert str_size_to_bytes('0G') == 0

    assert str_size_to_bytes('127') == 127
    assert str_size_to_bytes('2K') == 2 * 1024
    assert str_size_to_bytes('5M') == 5 * 1024 * 1024
    assert str_size_to_bytes('3G') == 3 * 1024 * 1024 * 1024
