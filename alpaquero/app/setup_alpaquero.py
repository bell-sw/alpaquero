#!/usr/bin/env python3

#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import sys


def main():
    from .application import Application
    from .palette import PALETTE

    app = Application(palette=PALETTE)
    app.run()


if __name__ == '__main__':
    sys.exit(main())
