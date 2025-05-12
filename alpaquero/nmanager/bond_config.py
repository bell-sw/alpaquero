#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

from typing import Optional

BOND_MODES = ('balance-rr', 'active-backup', 'balance-xor', 'broadcast',
              '802.3ad', 'balance-tlb', 'balance-alb')


def hash_policies_for_bond_mode(mode: str) -> list[str]:
    if mode in ('balance-alb', 'balance-tlb', 'balance-xor', '802.3ad'):
        return ['layer2', 'layer3+4', 'layer2+3', 'encap2+3', 'encap3+4']
    else:
        return []


def validate_bond_mode(mode: str):
    if mode not in BOND_MODES:
        raise ValueError('Unknown bond mode: {}'.format(mode))


def validate_bond_mode_and_policy(mode: str, hash_policy: Optional[str]):
    validate_bond_mode(mode)

    policies = hash_policies_for_bond_mode(mode)
    if (policies and (hash_policy not in policies)) or ((not policies) and hash_policy):
        raise ValueError("Unknown policy '{}' for mode '{}'".format(hash_policy, mode))


def is_valid_bond_name(name: str) -> bool:
    return False
