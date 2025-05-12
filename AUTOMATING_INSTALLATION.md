# Automating the Installation

The `alpaquero` offers a means to automate the installation process. For that to work
one should create a file describing the installation and pass it to the installer using the `-f` option.

This file is of the YAML format. It describes the installation with parameters provided below in this document.

The installer saves the YAML file for the current installation to `/root/setup.yaml` on the installed system.
This file can be used to repeat the installation on similar systems and/or as a starting point for customizations.

## Mandatory parameters

### Bootloader location (non-EFI only)

```yaml
bootloader_device: /dev/vdX
```

On non-EFI systems it's required to specify the device on which the bootloader will be installed.

### Network

Network configuration consists of 4 groups:

```yaml
network:
  hostname: <your-host-name>
  ipv4: <IPv4 configuration>
  ipv6: <IPv6 configuration>
  <interface configuration>
```

There must be at least one non-disabled IP configuration defined.

#### IPv4

IPv4 supports 3 methods: `disabled`, `dhcp` and `static`.

**IPv4 disabled:**

```yaml
network:
  <...>
  ipv4:
    method: disabled
  <...>
```

**IPv4 DHCP:**

```yaml
network:
  <...>
  ipv4:
    method: dhcp
  <...>
```

**IPv4 static**:

```yaml
network:
  <...>
  ipv4:
     method: static
     address: 192.168.0.1/24
     gateway: 192.168.0.254
     name_servers: [ '1.2.3.4' ]
     search_domains: [ 'your.search.domain' ]
  <...>
```

#### IPv6

IPv6 configuration is similar to IPv4, except:
* the yaml tag is `ipv6`
* addresses are in the IPv6 format (address/prefix)
* only `static` and `disabled` methods are supported

#### Interface configuration

Exactly one interface must be defined. This interface will be assigned
IPv4 and IPv6 configurations.

##### Regular Ethernet

```yaml
network:
  <...>
  interface:
    name: eth0
  <...>
```

Note, there is no `.` in the interface name.

##### VLAN over regular Ethernet

```yaml
network:
  <...>
  interface:
    name: eth0.50
  <...>
```

The VLAN tag goes after the `.` in the interface name.

##### WiFi interface

```yaml
network:
  <...>
  interface:
    name: wlan0
    type: wifi
    wifi_ssid: WiFiNetworkSSID
    wifi_psk: Super-Secret-Password
  <...>
```

##### Bond interface

```yaml
network:
  <...>
  interface:
  name: bond0
  type: bond
  bond_members: # must be regular ethernet interfaces
    - eth0
    - eth1
  bond_mode: 802.3ad
  bond_hash_policy: layer2
  <...>
```

where `bond_*` parameters have the same meaning as in `/etc/network/interfaces`.

##### VLAN over bond interface

Similar to the ordinary bond interface, but the vlan id is specified in the `name` field after `.`,
such as `bond0.15`.

### Package repositories

```yaml
repositories:
  keys: /dir/with/keys # optional
  urls: [ url1, url2 ]
```

The repositories from `urls` will be used to install all packages from and also will be configured
in `/etc/apk/repositories` on the installed system.

If access to these repositories requires keys other than those which are available on the host system,
the path to the new keys directory must be specified with the `keys` paramater. For example, this may be required
for cross-libc installations.

### Storage

Storage configuration is hierarchical: disks, partitions on these disks and, optionally, more complex storage
features (LVM, LUKS crypto volumes, software RAIDs).

Only `vfat`, `ext4` and `xfs` file systems are supported.

Regular partitions (i.e. partitions on disks) support the `esp` flag (for EFI System Partition) and the `bios_boot`
flag (to mark the partition for GRUB's stage 2 installation).

The boot order of services in OpenRC is `dmcrypt`, `mdadm-raid`, `lvm`. This means that the creation of a crypto volume
on a software RAID partition is not supported, but the creation of a software RAID on crypto volumes is fully supported.

`crypto_volumes`, `raids` and `volume_groups` tags should not be specified, if corresponding storage features are
not used.

Here is an example of a storage configuration utilizing all the features:

```yaml
storage:
  disks:
    - id: /dev/vda
      partitions:
        - id: efi
          size: 512M
          mount_point: /boot/efi
          fs_type: vfat
          flags: [ 'esp' ]
        - id: boot
          size: 1G
          fs_type: ext4
          mount_point: /boot
        - id: raid_vda
          size: 10G
          fs_type: raid_member
        - id: secret_data
          fs_type: crypto_partition
          crypto_passphrase: super-secret
    - id: /dev/vdb
      partitions:
        - id: raid_vdb
          size: 10G
          fs_type: raid_member
  crypto_volumes:
    - id: crypto_volume
      on_partition: secret_data
      fs_type: ext4
      fs_opts: [ 'ro' ]
      mount_point: /secret
  raids:
    - id: some_raid
      level: 1
      members: [ raid_vda, raid_vdb ]
      partitions:
        - id: pv1
          size: 5G
          fs_type: physical_volume
        - id: pv2
          fs_type: physical_volume
  volume_groups:
    - id: some_vg
      physical_volumes: [ pv1, pv2 ]
      logical_volumes:
        - id: root
          size: 2G
          fs_type: ext4
          mount_point: /
        - id: home
          fs_type: ext4
          fs_opts: [ 'noauto' ]
          mount_point: /home
```

### Timezone

```yaml
timezone: America/New_York
```

The time zone is specified as a path to the time zone file under `/usr/share/zoneinfo`.

### Users

```yaml
users:
  - name: user1
    password: <password hash>
    gecos: 'gecos for user1' # optional
    is_admin: false
  - name: admin
    password: <password hash>
    is_admin: true
```

The `root` user is always disabled, so it's recommended to define at least one user with admin
privileges (`is_admin: true`).

The password hash can be generated with Python's `crypt.crypt()` function.


## Optional parameters

### Enable/disable services

```yaml
services:
  disabled: ['svc1', 'svc2']
  enabled: ['svc3']
```

At first the _disabled_ list is processed, and then the _enabled_ one. So if one service is added to both the lists,
it will be enabled on the installed system.

### Extra packages

```yaml
extra_packages: [ 'pkg1', 'pkg2' ]
```

### Kernel cmdline arguments

```yaml
kernel:
  cmdline: [ 'quiet' ]
```

### Proxy

```yaml
proxy: http://host:port
```

This HTTP proxy will be used during the installation, and will be configured on the installed
system (in `/etc/profile.d/proxy.sh`).

### SecureBoot

```yaml
install_shim_bootloader: true
```

If `true`, `shim` and `grub-efi-signed` bootloaders will be installed.

### Swap file

```yaml
swap_file:
   path: /swapfile
   size: 512M
```

### Post installation scripts

```yaml
post_scripts:
  - interpreter: /bin/sh
    chroot: true # Optional, true by default
    script: cat /etc/passwd
  - interpreter: /usr/bin/python3
    chroot: false
    script: |
      import time
      print(time.time())
      print('Doing some work')
```

These scripts are executed after the installation is complete, but before the target file system is unmounted.

`chroot` determines whether the corresponding script should be executed inside the target chroot environment, or
in the environment the installer is running in. In the former case the target file system is available at `/`,
in the latter - at location pointed by the `TARGET_ROOT` environment variable.

The `script` content wil be passed to the standard input of the `interpreter` program.
