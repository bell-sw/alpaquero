#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
import os
from typing import Optional, Union, cast

import attrs

from alpaquero.smanager.manager import StorageManager
from alpaquero.smanager.storage_unit import Partition, StorageUnit, StorageUnitFlag, CryptoVolume
from alpaquero.smanager.file_system import FSType
from alpaquero.common.utils import run_cmd
from .installer import Installer
from .utils import read_key_or_fail, str_size_to_bytes, read_list


# Each unit id is unique in the file
#
# OpenRC starts dmcrypt, then mdadm-raid, then lvm. This means we cannot
# create a crypto volume on, say, a software raid partition, but we
# can create a software raid on crypto volumes.
#
# storage:
#   disks:
#     - id: /dev/vda
#       partitions:
#         - id: efi
#           size: 512M
#           mount_point: /boot/efi
#           fs_type: vfat
#           flags: [ 'esp' ]
#         - id: boot
#           size: 1G
#           fs_type: ext4
#           mount_point: /boot
#         - id: raid_vda
#           size: 10G
#           fs_type: raid_member
#         - id: secret_data
#           fs_type: crypto_partition
#           crypto_passphrase: super-secret
#     - id: /dev/vdb
#       partitions:
#         - id: raid_vdb
#           size: 10G
#           fs_type: raid_member
#   crypto_volumes:
#     - id: crypto_volume
#       on_partition: secret_data
#       fs_type: ext4
#       fs_opts: [ 'ro' ]
#       mount_point: /secret
#   raids:
#     - id: some_raid
#       level: 1
#       members: [ raid_vda, raid_vdb ]
#       partitions:
#         - id: pv1
#           size: 5G
#           fs_type: physical_volume
#         - id: pv2
#           fs_type: physical_volume
#   volume_groups:
#     - id: some_vg
#       physical_volumes: [ pv1, pv2 ]
#       logical_volumes:
#         - id: root
#           size: 2G
#           fs_type: ext4
#           mount_point: /
#         - id: home
#           fs_type: ext4
#           fs_opts: [ 'noauto' ]
#           mount_point: /home


@attrs.define
class UnitParams:
    id: str
    size: int
    fs_type: Optional[FSType]
    mount_point: Optional[str]
    crypto_passphrase: Optional[str]
    fs_opts: list[str] = attrs.field(default=attrs.Factory(list))
    flags: set[StorageUnitFlag] = attrs.field(default=attrs.Factory(set))

    @staticmethod
    def from_dict(data: dict) -> UnitParams:
        id = data.get('id', None)

        size = data.get('size', None)
        if size is None:
            size = 0
        else:
            size = str_size_to_bytes(str(size))

        fs_type = data.get('fs_type', None)
        if fs_type is not None:
            fs_type = FSType.from_str(fs_type)

        mount_point = data.get('mount_point', None)
        crypto_passphrase = data.get('crypto_passphrase', None)

        fs_opts = read_list(data, key='fs_opts', item_type=str, error_label='fs_opts')

        flags_s = read_list(data, key='flags', item_type=str, error_label='flags')
        flags = []
        for flag_s in flags_s:
            flags.append(StorageUnitFlag.from_str(flag_s))

        return UnitParams(id=id, size=size, fs_type=fs_type, fs_opts=fs_opts,
                          mount_point=mount_point, flags=flags,
                          crypto_passphrase=crypto_passphrase)


class StorageInstaller(Installer):
    def __init__(self, target_root: str, config: dict, event_receiver):
        self._yaml_tag = 'storage'
        super().__init__(name=self._yaml_tag, config=config,
                         event_receiver=event_receiver,
                         data_type=dict, target_root=target_root)

        # To maintain uniqueness among unit ids
        self._units: dict[str, StorageUnit] = {}
        self._bind_mounts = ('dev', 'proc', 'sys')

        self._smanager = StorageManager()
        self._smanager.mount_root_base = self.target_root
        self._has_disks = self._parse_disks()
        self._has_crypto = self._parse_crypto_volumes()
        self._has_raids = self._parse_raids()
        self._has_lvm = self._parse_volume_groups()
        self._validate()

        if self._has_raids:
            self.add_package('mdadm', 'mdadm-udev')
        if self._has_crypto:
            self.add_package('cryptsetup', 'cryptsetup-openrc')
        if self._has_lvm:
            self.add_package('lvm2')

        self._file_systems = set()
        for unit in self._units.values():
            if unit.fs_type is not None:
                self._file_systems.add(unit.fs_type)

        fs_to_pkg = {FSType.EXT4: 'e2fsprogs',
                     FSType.XFS: 'xfsprogs',
                     FSType.VFAT: 'dosfstools'}
        for fs in self._file_systems:
            pkg = fs_to_pkg.get(fs, None)
            if pkg is not None:
                self.add_package(pkg)

    def _add_unit(self, unit: StorageUnit):
        if unit.id in self._units:
            raise ValueError("Unit with id '{}' is already defined".format(unit.id))
        self._units[unit.id] = unit

    def _unit_by_id(self, id: str, fail: bool = True) -> Optional[StorageUnit]:
        unit = self._units.get(id, None)
        if fail and (unit is None):
            raise ValueError("Unknown unit id '{}'".format(id))
        return unit

    def _validate(self):
        if self._smanager.get_unit_by_mount_point('/') is None:
            raise ValueError('No / mount point defined')
        # Probably here will be more checks

    def _parse_disks(self) -> bool:
        yaml_key = 'disks'
        error_label = f'{self._yaml_tag}/{yaml_key}'
        disk_list = read_list(self._data, key=yaml_key, item_type=dict,
                              error_label=error_label)
        disk_created = False
        for i, disk_item in enumerate(disk_list):
            error_label = f'{error_label}/{i}'
            disk = self._smanager.add_disk(id=read_key_or_fail(disk_item, 'id', str,
                                                               error_label=f'{error_label}/id'))
            disk_created = True

            part_key = 'partitions'
            part_list = read_list(disk_item, key=part_key, item_type=dict,
                                  error_label=f'{error_label}/{part_key}')
            for part_item in part_list:
                params = UnitParams.from_dict(part_item)
                unit = disk.add_partition(id=params.id, size=params.size,
                                          fs_type=params.fs_type, fs_opts=params.fs_opts,
                                          mount_point=params.mount_point, flags=params.flags,
                                          crypto_passphrase=params.crypto_passphrase)
                self._add_unit(unit)
        return disk_created

    def _parse_raids(self) -> bool:
        yaml_key = 'raids'
        if yaml_key not in self._data:
            return False

        error_label = f'{self._yaml_tag}/{yaml_key}'
        raid_list = read_list(self._data, key=yaml_key, item_type=dict,
                              error_label=error_label)
        raid_created = False
        for i, raid_item in enumerate(raid_list):
            error_label = f'{error_label}/{i}'
            raid_id = read_key_or_fail(raid_item, 'id', str, error_label=f'{error_label}/id')
            level = read_key_or_fail(raid_item, 'level', int, error_label=f'{error_label}/level')
            metadata = read_key_or_fail(raid_item, 'metadata', str, error_label=f'{error_label}/metadata')
            if not metadata:
                metadata = '1.2'

            members_key = 'members'
            members_list = read_list(raid_item, key=members_key, item_type=str,
                                     error_label=f'{error_label}/{members_key}')
            members = []
            for m_item in members_list:
                part = cast(Union[CryptoVolume, Partition], self._unit_by_id(m_item))
                members.append(part)

            raid = self._smanager.add_raid(id=os.path.join('/dev/md', raid_id),
                                           level=level, members=members, metadata=metadata)
            raid_created = True

            part_key = 'partitions'
            part_list = read_list(raid_item, key=part_key, item_type=dict,
                                  error_label=f'{error_label}/{part_key}')
            for part_item in part_list:
                params = UnitParams.from_dict(part_item)
                unit = raid.add_partition(id=params.id, size=params.size,
                                          fs_type=params.fs_type, fs_opts=params.fs_opts,
                                          mount_point=params.mount_point, flags=params.flags,
                                          crypto_passphrase=params.crypto_passphrase)
                self._add_unit(unit)

        return raid_created

    def _parse_crypto_volumes(self) -> bool:
        yaml_key = 'crypto_volumes'
        if yaml_key not in self._data:
            return False

        error_label = f'{self._yaml_tag}/{yaml_key}'
        crypto_list = read_list(self._data, key=yaml_key, item_type=dict,
                                error_label=error_label)
        volume_created = False
        for i, crypto_item in enumerate(crypto_list):
            error_label = f'{error_label}/{i}'
            params = UnitParams.from_dict(crypto_item)
            part_id = read_key_or_fail(crypto_item, 'on_partition', str,
                                       error_label=f'{error_label}/on_partition')
            part = cast(Partition, self._unit_by_id(part_id))
            unit = self._smanager.cryptsetup.add_volume(id=params.id, partition=part,
                                                        fs_type=params.fs_type, fs_opts=params.fs_opts,
                                                        mount_point=params.mount_point)
            self._add_unit(unit)
            volume_created = True

        return volume_created

    def _parse_volume_groups(self) -> bool:
        yaml_key = 'volume_groups'
        if yaml_key not in self._data:
            return False

        error_label = f'{self._yaml_tag}/{yaml_key}'
        vg_list = read_list(self._data, key=yaml_key, item_type=dict,
                            error_label=error_label)
        vg_created = False
        for i, vg_item in enumerate(vg_list):
            error_label = f'{error_label}/{i}'
            vg_id = read_key_or_fail(vg_item, 'id', str, error_label=f'{error_label}/id')

            pv_key = 'physical_volumes'
            pv_list = read_list(data=vg_item, key=pv_key, item_type=str,
                                error_label=f'{error_label}/{pv_key}')
            physical_volumes = []
            for pv_item in pv_list:
                p_volume = cast(Union[Partition, CryptoVolume], self._unit_by_id(pv_item))
                physical_volumes.append(p_volume)

            vg = self._smanager.add_vg(id=vg_id, physical_volumes=physical_volumes)
            vg_created = True

            lv_key = 'logical_volumes'
            lv_list = read_list(data=vg_item, key=lv_key, item_type=dict,
                                error_label=f'{error_label}/{lv_key}')
            for lv_item in lv_list:
                params = UnitParams.from_dict(lv_item)
                unit = vg.add_lv(id=params.id, size=params.size,
                                 fs_type=params.fs_type, fs_opts=params.fs_opts,
                                 mount_point=params.mount_point)
                self._add_unit(unit)

        return vg_created

    @property
    def efi_mount_point(self) -> Optional[str]:
        for unit in self._smanager.storage_units:
            if StorageUnitFlag.ESP in unit.flags:
                return unit.mount_point

    def apply(self):
        self._event_receiver.start_event('Creating and mounting file systems')
        # busybox's mount fails if no fs-related module is loaded
        for fs in self._file_systems:
            run_cmd(args=['modprobe', str(fs)], ignore_status=True,
                    event_receiver=self._event_receiver)

        self._smanager.create_filesystems()
        self._smanager.mount()

        for mount in self._bind_mounts:
            src = os.path.join('/', mount)
            dst = self.abs_target_path(mount)
            os.makedirs(dst)
            run_cmd(args=['mount', '-o', 'bind', src, dst], event_receiver=self._event_receiver)

    def post_apply(self):
        self._event_receiver.start_event('Updating storage configuration')

        self._smanager.write_fstab(self.abs_target_path('/etc/fstab'))

        if self._has_raids:
            self._smanager.write_mdadm_conf(self.abs_target_path('/etc/mdadm.conf'))
            for service in ('mdadm', 'mdadm-raid'):
                self.enable_service(service=service, runlevel='boot')

        # TODO: write dmcrypt config only for non-root partitions
        # if self._has_crypto:
        #     self._smanager.write_dmcrypt(self.abs_target_path('/etc/conf.d/dmcrypt'))
        #     self.enable_service(service='dmcrypt', runlevel='sysinit')

        if self._has_lvm:
            self.enable_service(service='lvm', runlevel='boot')

    def cleanup(self):
        self._event_receiver.start_event('Unmounting file systems')
        for mount in self._bind_mounts:
            run_cmd(args=['umount', self.abs_target_path(mount)],
                    event_receiver=self._event_receiver)
        self._smanager.unmount()
        self._smanager.deactivate_block_devices()
