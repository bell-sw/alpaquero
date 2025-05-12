#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from __future__ import annotations
from typing import TYPE_CHECKING

import yaml
import pytest

from alpaquero.installers.installer import InstallerException
from alpaquero.installers.storage import StorageInstaller
from alpaquero.smanager.disk import Disk
from .utils import new_installer

if TYPE_CHECKING:
    from alpaquero.smanager.manager import StorageManager

MB = 1024 * 1024
GB = 1024 * 1024 * 1024
DISK_SIZE = 10 * GB


@pytest.fixture
def mock_host_disks(monkeypatch):
    def init(self: Disk, manager: StorageManager, id: str):
        # We don't check that the block device file actually exists
        super(Disk, self).__init__(manager=manager, id=id, size=DISK_SIZE)

    monkeypatch.setattr('alpaquero.smanager.disk.Disk.__init__', init)


def create_installer(config: dict) -> StorageInstaller:
    return new_installer(StorageInstaller, config=config)


def test_no_storage():
    with pytest.raises(InstallerException):
        create_installer({})


def test_duplicate_disk_ids(mock_host_disks):
    config_yaml = '''
storage:
  disks:
  - id: /dev/vda
    partitions:
    - id: boot
      size: 512M
      fs_type: ext4
      mount_point: /boot
  - id: /dev/vda
    partitions:
    - id: root
      fs_type: ext4
      mount_point: /
    '''
    with pytest.raises(ValueError, match=r'(?i)already exists'):
        create_installer(yaml.safe_load(config_yaml))


def test_duplicate_unit_ids(mock_host_disks):
    config_yaml1 = '''
storage:
  disks:
  - id: /dev/vda
    partitions:
    - id: boot
      size: 512M
      fs_type: ext4
      mount_point: /boot
    - id: boot
      fs_type: ext4
      mount_point: /    
    '''
    config_yaml2 = '''
storage:
  disks:
  - id: /dev/vda
    partitions:
    - id: boot
      size: 512M
      fs_type: ext4
      mount_point: /boot
    - id: crypto_part
      fs_type: crypto_partition
      crypto_passphrase: super-secret
  crypto_volumes:
  - id: boot
    on_partition: crypto_part
    fs_type: ext4
    mount_point: /
    '''
    for config_yaml in (config_yaml1, config_yaml2):
        with pytest.raises(ValueError, match="'boot'"):
            create_installer(yaml.safe_load(config_yaml))


def test_reference_to_unknown_unit(mock_host_disks):
    config_yaml = '''
storage:
  disks:
  - id: /dev/vda
    partitions:
    - id: boot
      size: 512M
      fs_type: ext4
      mount_point: /boot
    - id: crypto_part
      fs_type: crypto_partition
      crypto_passphrase: super-secret
  crypto_volumes:
  - id: boot
    on_partition: unknown_unit_id
    fs_type: ext4
    mount_point: /
    '''
    with pytest.raises(ValueError, match="'unknown_unit_id'"):
        create_installer(yaml.safe_load(config_yaml))


def test_no_root_mount_point(mock_host_disks):
    config_yaml = '''
storage:
  disks:
  - id: /dev/vda    
    partitions:
    - id: boot
      size: 512M
      fs_type: ext4
      mount_point: /boot
    '''
    with pytest.raises(ValueError, match=r'(?i)no / '):
        create_installer(yaml.safe_load(config_yaml))


def test_invalid_fs_type(mock_host_disks):
    config_yaml = '''
storage:
  disks:
  - id: /dev/vda    
    partitions:
    - id: root
      fs_type: invalid_fs_type
      mount_point: /
    '''
    with pytest.raises(ValueError, match=r'(?i)unknown file system'):
        create_installer(yaml.safe_load(config_yaml))


def test_no_fs_type_with_mount_point(mock_host_disks):
    config_yaml = '''
storage:
  disks:
  - id: /dev/vda    
    partitions:
    - id: root
      mount_point: /
    '''
    with pytest.raises(ValueError, match=r'(?i)fs_type is not set'):
        create_installer(yaml.safe_load(config_yaml))


def test_disks(mock_host_disks):
    config_yaml = '''
storage:
  disks:
  - id: /dev/vda
    partitions:
    - id: boot
      size: 512M
      fs_type: ext4
      mount_point: /boot    
    - id: root
      fs_type: ext4
      mount_point: /
    '''
    create_installer(yaml.safe_load(config_yaml))


def test_disk_id_invalid_type():
    config_yaml = '''
storage:
  disks:
  - id: false
    partitions:
    - id: root
      size: 4G
      fs_type: ext4
      mount_point: /
    '''
    with pytest.raises(ValueError, match="'storage/disks/0/id'"):
        create_installer(yaml.safe_load(config_yaml))


def test_disks_invalid_type(mock_host_disks):
    config_yaml1 = '''
storage:
  disks: 'should be a list'    
    '''
    config_yaml2 = '''
storage:
  disks: ['must be a dict', 'bla']    
    '''
    for config_yaml in (config_yaml1, config_yaml2):
        with pytest.raises(ValueError, match="'storage/disks'"):
            create_installer(yaml.safe_load(config_yaml))


def test_crypto_volume(mock_host_disks):
    config_yaml = '''
storage:
  disks:
  - id: /dev/vda
    partitions:
    - id: boot
      size: 512M
      fs_type: ext4
      mount_point: /boot
    - id: crypto_part
      fs_type: crypto_partition
      crypto_passphrase: super-secret    
  crypto_volumes:
  - id: root
    on_partition: crypto_part
    fs_type: ext4
    mount_point: /
    '''
    config = yaml.safe_load(config_yaml)
    crypto_part = config['storage']['disks'][0]['partitions'][1]
    crypto_volume = config['storage']['crypto_volumes'][0]

    installer = create_installer(config)
    for pkg in ('cryptsetup', 'cryptsetup-openrc'):
        assert pkg in installer.packages

    crypto_volume['on_partition'] = []  # type: ignore
    with pytest.raises(ValueError, match="'storage/crypto_volumes/0/on_partition'"):
        create_installer(config)

    errmsg = 'fs opts or mount point'
    crypto_volume['on_partition'] = 'crypto_part'
    crypto_part['fs_opts'] = ['bios_boot']
    with pytest.raises(ValueError, match=errmsg):
        create_installer(config)
    del crypto_part['fs_opts']
    crypto_part['mount_point'] = '/some/mount/point'
    with pytest.raises(ValueError, match=errmsg):
        create_installer(config)

    del crypto_part['mount_point']
    del crypto_part['crypto_passphrase']
    with pytest.raises(ValueError, match=r'(?i)passphrase'):
        create_installer(config)


def test_raids(mock_host_disks):
    config_yaml = '''
storage:
  disks:
  - id: /dev/vda
    partitions:
    - id: boot
      size: 512M
      fs_type: ext4
      mount_point: /boot
    - id: raid_vda
      fs_type: raid_member
  - id: /dev/vdb
    partitions:
    - id: raid_vdb
      fs_type: raid_member
  raids:
  - id: some_raid
    level: 1
    members: [ raid_vda, raid_vdb ]
    partitions:
    - id: root
      fs_type: ext4
      mount_point: /
    '''
    config = yaml.safe_load(config_yaml)
    raid = config['storage']['raids'][0]

    installer = create_installer(config)
    for pkg in ('mdadm', 'mdadm-udev'):
        assert pkg in installer.packages

    del raid['level']
    with pytest.raises(ValueError, match="RAID1"):
        create_installer(config)

    raid['level'] = 1
    del raid['members']
    with pytest.raises(ValueError, match="members"):
        create_installer(config)

    raid['members'] = 'invalid data'
    with pytest.raises(ValueError, match="'storage/raids/0/members'"):
        create_installer(config)


def test_volume_groups(mock_host_disks):
    config_yaml = '''
storage:
  disks:
  - id: /dev/vda
    partitions:
    - id: boot
      size: 512M
      fs_type: ext4
      mount_point: /boot
    - id: pv
      fs_type: physical_volume
  volume_groups:
  - id: some_vg
    physical_volumes: [pv]
    logical_volumes:
    - id: root
      fs_type: ext4
      mount_point: /
    '''
    config = yaml.safe_load(config_yaml)
    volume_group = config['storage']['volume_groups'][0]

    installer = create_installer(config)
    assert 'lvm2' in installer.packages

    del volume_group['physical_volumes']
    with pytest.raises(ValueError, match=r'(?i)physical volume'):
        create_installer(config)

    volume_group['physical_volumes'] = 'invalid data'
    with pytest.raises(ValueError, match="'storage/volume_groups/0/physical_volumes'"):
        create_installer(config)


def test_invalid_size(mock_host_disks):
    config_yaml = '''
storage:
  disks:
  - id: /dev/vda
    partitions:
    - id: root
      size: 100M  
      fs_type: ext4
      mount_point: /
    '''
    config = yaml.safe_load(config_yaml)
    for size in ('1m', '-12M', '23z', 'bla'):
        config['storage']['disks'][0]['partitions'][0]['size'] = size
        with pytest.raises(ValueError, match=r'(?i)size format'):
            create_installer(config)


def test_no_free_space(mock_host_disks):
    config_yaml = f'''
storage:
  disks:
  - id: /dev/vda
    partitions:
    - id: root
      size: {DISK_SIZE * 10}  
      fs_type: ext4
      mount_point: /
    '''
    with pytest.raises(ValueError, match=r'(?i)free space'):
        create_installer(yaml.safe_load(config_yaml))


def test_fs_opts(mock_host_disks):
    config_yaml = f'''
storage:
  disks:
  - id: /dev/vda
    partitions:
    - id: root
      size: 4G
      fs_type: ext4
      mount_point: /
    - id: test-part
      fs_type: ext4
      fs_opts: []
    '''
    config = yaml.safe_load(config_yaml)
    part = config['storage']['disks'][0]['partitions'][1]

    create_installer(config)

    part['fs_opts'] = ['ro']
    create_installer(config)

    for invalid_opts in ('invalid_data', [False]):
        part['fs_opts'] = invalid_opts
        with pytest.raises(ValueError, match="'fs_opts'"):
            create_installer(config)


def test_flags(mock_host_disks):
    config_yaml = f'''
storage:
  disks:
  - id: /dev/vda
    partitions:
    - id: bios
      size: 2M
      flags: ['bios_boot']
    - id: efi
      size: 512M
      fs_type: vfat
      flags: ['esp']
    - id: root
      size: 4G
      fs_type: ext4
      mount_point: /
    '''
    config = yaml.safe_load(config_yaml)
    parts = config['storage']['disks'][0]['partitions']
    bios_part = parts[0]

    create_installer(config)

    bios_part['flags'] = []
    create_installer(config)

    for invalid_flags in ('invalid_data', [False]):
        bios_part['flags'] = invalid_flags
        with pytest.raises(ValueError, match="'flags'"):
            create_installer(config)

    bios_part['flags'] = ['esp']
    with pytest.raises(ValueError, match='ESP'):
        create_installer(config)
