# Storage Manager

Define the required storage layout and then make corresponding modifications to the system.

## Example

```python
from smanager.manager import StorageManager
from smanager.storage_unit import StorageUnitFlag
from smanager.file_system import FSType

manager = StorageManager()
vdb = manager.add_disk(id='/dev/vdb')
vdc = manager.add_disk(id='/dev/vdc')

efi_size = 300*1024*1024
boot_size = 2*1024*1024*1024

vdb1 = vdb.add_partition(id='efi_part', fs_type=FSType.VFAT, fs_opts=['umask=0077'],
                         size=efi_size, mount_point='/boot/efi',
                         flags=[StorageUnitFlag.ESP])
vdb2 = vdb.add_partition(id='boot_part', fs_type=FSType.EXT4, size=boot_size,
                         mount_point='/boot')
vdb3 = vdb.add_partition(id='crypto_part', fs_type=FSType.CRYPTO_PARTITION,
                         crypto_passphrase='super-secret1')
crypto_vdb3 = manager.cryptsetup.add_volume(id='crypto-vdb3', partition=vdb3,
                                            fs_type=FSType.RAID_MEMBER)

vdc1 = vdc.add_partition(id='crypto_part', fs_type=FSType.CRYPTO_PARTITION,
                         crypto_passphrase='super-secret2')
crypto_vdc1 = manager.cryptsetup.add_volume(id='crypto-vdc1', partition=vdc1,
                                            fs_type=FSType.RAID_MEMBER)

raid = manager.add_raid(id='/dev/md/raid', level=1, members=[crypto_vdb3, crypto_vdc1])
raidp1 = raid.add_partition(id='pv', fs_type=FSType.PHYSICAL_VOLUME)

vg = manager.add_vg(id='some_vg', physical_volumes=[raidp1])
lv_swap = vg.add_lv(id='swap', fs_type=FSType.SWAP, size=2*1024*1024*1024)
lv_root = vg.add_lv(id='root', fs_type=FSType.XFS, mount_point='/')

manager.create_filesystems()
manager.write_fstab('/tmp/fstab')
manager.write_dmcrypt('/etc/conf.d/dmcrypt')
manager.write_mdadm_conf('/etc/mdadm.conf')

manager.mount_root_base='/tmp/root'
manager.mount()
```

## TODO
 - Add tests
 - Allow creation of file systems on Disk and RAID