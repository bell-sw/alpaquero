#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import os
import re

import attrs

HWDATA_PCI = '/usr/share/hwdata/pci.ids'
HWDATA_USB = '/usr/share/hwdata/usb.ids'

UNKNOWN_VENDOR = 'Unknown vendor'
UNKNOWN_MODEL = 'Unknown model'


@attrs.define
class DeviceIdentification:
    vendor: str
    model: str


def _get_ids_from_uevent(pattern: str, uevent_path: str) -> tuple[int, int]:
    m = find_match_in_file(pattern, uevent_path)
    if not m:
        raise RuntimeError("Could not find pattern '{}' in ''".format(
            pattern, uevent_path))
    vendor_id = int(m.group(1), 16)
    model_id = int(m.group(2), 16)
    return vendor_id, model_id


def read_one_line(path: str) -> str:
    with open(path, 'r') as file:
        return file.readline().strip()


def find_match_in_file(line_pattern: str, path: str):
    with open(path, 'r') as file:
        for line in file:
            m = re.match(line_pattern, line.strip())
            if m:
                return m
    return None


def lookup_hwdata(hwdata_path: str, vendor_id: int, device_id: int) -> DeviceIdentification:
    vendor_pattern = re.compile(r'^([0-9a-fA-F]+)\s+(.+)$')
    device_pattern = re.compile(r'^\t([0-9a-fA-F]+)\s+(.+)$')

    vendor = None
    device = None
    try:
        with open(hwdata_path, 'r', errors='ignore') as file:
            for line in file:
                line = line.rstrip()

                vm = vendor_pattern.match(line)
                if vm:
                    if vendor:
                        break
                    elif vendor_id == int(vm.group(1), 16):
                        vendor = vm.group(2)
                        continue

                if vendor:
                    dm = device_pattern.match(line)
                    if dm and (device_id == int(dm.group(1), 16)):
                        device = dm.group(2)
                        break
    except FileNotFoundError:
        pass

    if not vendor:
        vendor = UNKNOWN_VENDOR
    if not device:
        device = UNKNOWN_MODEL

    return DeviceIdentification(vendor=vendor, model=device)


def identify_usb_device(device_path: str) -> DeviceIdentification:
    uevent_path = os.path.join(device_path, 'uevent')
    vendor_id, model_id = _get_ids_from_uevent(r'^PRODUCT=([0-9a-fA-F]+)/([0-9a-fA-F]+)/[0-9a-fA-F]+$',
                                               uevent_path)
    return lookup_hwdata(HWDATA_USB, vendor_id=vendor_id, device_id=model_id)


def identify_pci_device(device_path: str) -> DeviceIdentification:
    vendor_id = int(read_one_line(os.path.join(device_path, 'vendor')), 16)
    device_id = int(read_one_line(os.path.join(device_path, 'device')), 16)

    return lookup_hwdata(HWDATA_PCI, vendor_id=vendor_id, device_id=device_id)


def identify_virtio_device(device_path: str) -> DeviceIdentification:
    device_path = os.path.realpath(os.path.join(device_path, '..'))
    return identify_pci_device(device_path)


def get_device_subsystem(device_path: str) -> str:
    subsystem_path = os.path.join(device_path, 'subsystem')
    if not os.path.islink(subsystem_path):
        raise ValueError("'{}' is not a symbolic link".format(subsystem_path))
    return os.path.basename(os.path.realpath(subsystem_path))


def identify_device(device_path: str) -> DeviceIdentification:
    subsystem = get_device_subsystem(device_path)
    if subsystem == 'pci':
        return identify_pci_device(device_path)
    elif subsystem == 'virtio':
        return identify_virtio_device(device_path)
    elif subsystem == 'usb':
        return identify_usb_device(device_path)
    else:
        return DeviceIdentification(vendor=UNKNOWN_VENDOR, model=UNKNOWN_MODEL)
