#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import os

from attrs import define

REGIONS = [
    'Africa',
    'America',
    'Antarctica',
    'Arctic',
    'Asia',
    'Atlantic',
    'Australia',
    'Europe',
    'Indian',
    'Pacific',
    'Etc',
]
ZONEINFO_DIR = '/usr/share/zoneinfo'


@define
class TimezoneRegion:
    name: str
    cities: list[str]


def read_regions() -> list[TimezoneRegion]:
    regions = []
    for d in REGIONS:
        cities = []
        for dirpath, _, filenames in os.walk(os.path.join(ZONEINFO_DIR, d)):
            for filename in filenames:
                p = os.path.join(dirpath, filename)
                np = os.path.normpath(p)
                cities.append('/'.join(np.split('/')[5:]))
           
        regions.append(TimezoneRegion(d, sorted(cities)))
    return regions
