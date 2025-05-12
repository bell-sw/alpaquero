#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import re
from typing import Type, TypeVar, Iterable, Optional

TV = TypeVar(name='TV')


def read_key_or_fail(data: dict, key: str, value_type: Type[TV],
                     error_label: Optional[str] = None) -> TV:
    if error_label is None:
        error_label = key
    value = data.get(key, value_type())
    if not isinstance(value, value_type):
        raise ValueError("'{}' must be of type '{}', but is '{}'".format(
            error_label, str(value_type), type(value)))
    return value


def validate_types_of_elements(iterable: Iterable, item_type: Type[TV], error_label: str):
    for x in iterable:
        if not isinstance(x, item_type):
            raise ValueError("All '{}' elements must be of type '{}', but '{}' is of type '{}'".format(
                error_label, item_type, x, type(x)))


def read_list(data: dict, key: str, item_type: Type[TV], error_label: str) -> list[TV]:
    lst = read_key_or_fail(data, key, list, error_label=error_label)
    if lst:
        validate_types_of_elements(lst, item_type=item_type, error_label=error_label)
    return lst


def str_size_to_bytes(size: str) -> int:
    m = re.match(r'^([0-9]+)([KMG])?$', size)
    if not m:
        raise ValueError('Invalid size format: {}'.format(size))

    nbytes = int(m.group(1))
    suffixes = {'K': 1024,
                'M': 1024 * 1024,
                'G': 1024 * 1024 * 1024}
    suffix = m.group(2)
    if suffix:
        nbytes *= suffixes.get(suffix)

    return nbytes
