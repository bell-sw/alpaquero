#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
from typing import Optional, TYPE_CHECKING
import json
import logging

import attrs
import yaml

from alpaquero.app.distro import DISTRO
from alpaquero.smanager.manager import StorageManager
from alpaquero.smanager.file_system import FSType
from alpaquero.smanager.storage_unit import Partition, StorageUnit, StorageUnitFlag, CryptoVolume
from alpaquero.smanager.disk import Disk as SM_Disk
from alpaquero.smanager.raid import RAID
from alpaquero.smanager.lvm import VolumeGroup
from alpaquero.common.utils import run_cmd
from alpaquero.views.storage import StorageView, StorageViewData
from .controller import Controller

if TYPE_CHECKING:
    from alpaquero.app.application import Application

log = logging.getLogger('controllers.storage')


@attrs.define
class Disk:
    path: str
    size: int
    model: Optional[str]
    serial: Optional[str]


def scan_host_disks() -> list[Disk]:
    res = run_cmd(args=['lsblk', '-J', '-b', '--nodeps',
                        '-o', 'path,type,size,model,serial'])
    data = json.loads(res.stdout)
    disks = []
    for blkdev in data['blockdevices']:
        if blkdev['type'] != 'disk':
            continue
        for opt_name in ('model', 'serial'):
            if blkdev[opt_name]:
                blkdev[opt_name] = blkdev[opt_name].strip()
            if not blkdev[opt_name]:
                blkdev[opt_name] = None
        disk = Disk(path=blkdev['path'], size=blkdev['size'],
                    model=blkdev['model'], serial=blkdev['serial'])
        log.debug('Found disk: {}'.format(disk))
        disks.append(disk)
    return disks


class StorageController(Controller):
    MB = 1024 * 1024
    GB = 1024 * MB

    # Size of /boot/efi for EFI installations
    BOOT_EFI_SIZE = 512 * MB
    # Size of the bios_boot partition for non-EFI installations
    BIOS_BOOT_SIZE = MB
    # Size of /boot
    BOOT_SIZE = 512 * MB
    # A bare installation takes less than 100M.
    # All liberica{8,11,17} and liberica{8,11,17} lite take < 1.2G.
    # liberica{11,17}-nik both take ~ 1G.
    ROOT_MIN_SIZE = 4 * GB

    def __init__(self, app: Application):
        super().__init__(app)

        self._smanager: Optional[StorageManager] = None
        self._smanager_needs_reset = False

        self._available_disks = scan_host_disks()
        self._selected_disk: Optional[Disk] = None
        self._file_system = 'xfs'
        self._use_lvm = False
        self._crypto_passphrase: Optional[str] = None

    def _reset_smanager(self):
        # There is a bug - if we don't have a separate /boot
        # and / is on xfs, and we reboot after a musl and kernel apk updates,
        # busybox init may fail to correctly umount -o ro /, thus leaving the fs corrupted.
        # This, in turn, may leave files in /boot corrupted, so grub will be unable
        # to load them on the next boot.
        # So we create /boot to avoid this situation.
        create_boot = True
        create_esp = self._app.is_efi()

        req_size = self.ROOT_MIN_SIZE
        if create_esp:
            req_size += self.BOOT_EFI_SIZE
        else:
            req_size += self.BIOS_BOOT_SIZE
        if create_boot:
            req_size += self.BOOT_SIZE
        if self._selected_disk.size < req_size:
            raise ValueError("Not enough space on '{}': its size is {}, but {} is required".format(
                self._selected_disk.path, self._selected_disk.size, req_size))

        root_fs_type = {'ext4': FSType.EXT4, 'xfs': FSType.XFS}[self._file_system]

        smanager = StorageManager()

        disk = smanager.add_disk(id=self._selected_disk.path)
        if create_esp:
            disk.add_partition(id='efi', size=self.BOOT_EFI_SIZE,
                               mount_point='/boot/efi',
                               fs_type=FSType.VFAT,
                               fs_opts=['umask=0077'],
                               flags=[StorageUnitFlag.ESP])
        else:
            disk.add_partition(id='bios_boot', size=self.BIOS_BOOT_SIZE,
                               flags=[StorageUnitFlag.BIOS_BOOT])

        if create_boot:
            disk.add_partition(id='boot', size=self.BOOT_SIZE,
                               mount_point='/boot', fs_type=root_fs_type)

        if self._use_lvm:
            if self._crypto_passphrase:
                crypto_part = disk.add_partition(id='crypto_part', fs_type=FSType.CRYPTO_PARTITION,
                                                 crypto_passphrase=self._crypto_passphrase)
                pv = smanager.cryptsetup.add_volume(id='pv', fs_type=FSType.PHYSICAL_VOLUME,
                                                    partition=crypto_part)
            else:
                pv = disk.add_partition(id='pv', fs_type=FSType.PHYSICAL_VOLUME)

            vg = smanager.add_vg(id=f'{DISTRO}_vg', physical_volumes=[pv])
            vg.add_lv(id='root', fs_type=root_fs_type, mount_point='/')
        else:
            if self._crypto_passphrase:
                crypto_part = disk.add_partition(id='crypto_part', fs_type=FSType.CRYPTO_PARTITION,
                                                 crypto_passphrase=self._crypto_passphrase)
                smanager.cryptsetup.add_volume(id='root', fs_type=root_fs_type,
                                               partition=crypto_part, mount_point='/')
            else:
                disk.add_partition(id='root', fs_type=root_fs_type, mount_point='/')

        # If/when we enable user-defined storage configurations, this check
        # will go into a separate method
        if smanager.get_unit_by_mount_point('/') is None:
            raise ValueError('No / mount point defined')

        self._smanager = smanager

    def make_ui(self):
        data = StorageViewData(selected_disk=self._selected_disk,
                               file_system=self._file_system,
                               use_lvm=self._use_lvm,
                               crypto_passphrase=self._crypto_passphrase)
        return StorageView(self, self._available_disks[:], data)

    def done(self, data: StorageViewData):
        if self._selected_disk != data.selected_disk:
            self._selected_disk = data.selected_disk
            self._smanager_needs_reset = True
        if self._file_system != data.file_system:
            self._file_system = data.file_system
            self._smanager_needs_reset = True
        if self._use_lvm != data.use_lvm:
            self._use_lvm = data.use_lvm
            self._smanager_needs_reset = True
        if self._crypto_passphrase != data.crypto_passphrase:
            self._crypto_passphrase = data.crypto_passphrase
            self._smanager_needs_reset = True

        if self._smanager_needs_reset:
            try:
                self._reset_smanager()
                self._smanager_needs_reset = False
            except (TypeError, ValueError) as exc:
                self._app.show_error_message(str(exc))
                return
        log.debug('Selected disk: {}, use lvm: {}, crypto passphrase: {}'.format(
            self._selected_disk, self._use_lvm, self._crypto_passphrase))
        self._app.next_screen()

    def cancel(self):
        self._app.prev_screen()

    def to_yaml(self) -> str:
        def _unit_to_dict(unit: StorageUnit) -> dict:
            res = {'id': unit.id}
            if not unit.use_all_available_space:
                res['size'] = unit.size
            if unit.fs_type:
                res['fs_type'] = str(unit.fs_type)
            if unit.fs_opts:
                res['fs_opts'] = [str(o) for o in unit.fs_opts]
            if unit.mount_point:
                res['mount_point'] = unit.mount_point
            if unit.flags:
                res['flags'] = [str(f) for f in unit.flags]
            return res

        def _part_to_dict(part: Partition) -> dict:
            res = _unit_to_dict(part)
            if part.crypto_passphrase:
                res['crypto_passphrase'] = part.crypto_passphrase
            return res

        def _crypto_volume_to_dict(vol: CryptoVolume) -> dict:
            res = _unit_to_dict(vol)
            res.pop('size', None)
            res['on_partition'] = vol.partition.id
            return res

        storage_data = {}

        for disk in self._smanager.get_devices_by_type(SM_Disk):
            entry = {'id': disk.block_device,
                     'partitions': []}
            for part in disk.partitions:
                entry['partitions'].append(_part_to_dict(part))
            storage_data.setdefault('disks', []).append(entry)

        for volume in self._smanager.cryptsetup.volumes:
            storage_data.setdefault('crypto_volumes', []).append(_crypto_volume_to_dict(volume))

        for raid in self._smanager.get_devices_by_type(RAID):
            entry = {'id': raid.id,
                     'level': raid.level,
                     'members': [m.id for m in raid.members],
                     'partitions': []}
            for part in raid.partitions:
                entry['partitions'].append(_part_to_dict(part))
            storage_data.setdefault('raids', []).append(entry)

        for vg in self._smanager.get_devices_by_type(VolumeGroup):
            entry = {'id': vg.id,
                     'physical_volumes': [pv.id for pv in vg.physical_volumes],
                     'logical_volumes': []}
            for lv in vg.logical_volumes:
                entry['logical_volumes'].append(_unit_to_dict(lv))
            storage_data.setdefault('volume_groups', []).append(entry)

        data = {}
        if not self._app.is_efi():
            data['bootloader_device'] = self._selected_disk.path
        data['storage'] = storage_data

        yaml_data = yaml.dump(data)
        log.debug('export to yaml: {}'.format(yaml_data))
        return yaml_data
