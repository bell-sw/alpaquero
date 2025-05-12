#  SPDX-FileCopyrightText: 2023 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from attrs import define

# Distribution name. Used mostly in internal logic,
# in apk repo paths, labels, identifiers etc.
# Should be a single word of alphanumeric characters.
DISTRO = 'alpaquita'

# Distribution name. Shown to the user.
DISTRO_NAME = 'Alpaquita Linux'

DISTRO_REPO_BASE_URL = 'https://packages.bell-sw.com'


@define
class PackageDescription:
    description: str
    package: str


DISTRO_JDK8 = PackageDescription(description='Liberica Standard JDK 8',
                                 package='liberica8')
DISTRO_JDK11 = PackageDescription(description='Liberica Standard JDK 11',
                                  package='liberica11')
DISTRO_JDK17 = PackageDescription(description='Liberica Standard JDK 17',
                                  package='liberica17')
DISTRO_JDK21 = PackageDescription(description='Liberica Standard JDK 21',
                                  package='liberica21')
DISTRO_NIK23_17 = PackageDescription(description='Liberica Native Image Kit 23 (Java 17)',
                                     package='liberica-nik-23-17')
DISTRO_NIK23_21 = PackageDescription(description='Liberica Native Image Kit 23 (Java 21)',
                                     package='liberica-nik-23-21')
DISTRO_NIK24_22 = PackageDescription(description='Liberica Native Image Kit 24 (Java 22)',
                                     package='liberica-nik-24-22')
