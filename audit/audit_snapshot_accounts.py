"""Check which snapshot bundles or files contain account records."""

import json
from pathlib import Path

target_accounts = [
    'account_6440', 'account_410', 'account_5334', 'account_3136',
    'account_5684', 'account_3866', 'account_5482', 'account_7012',
    'account_4163', 'account_4857', 'account_8858'
]

for p in Path('dataset/evidence').rglob('*'):
    if p.is_file() and p.suffix in ('.json', '.sql', '.txt'):
        try:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                found = [a for a in target_accounts if a in content]
                if found:
                    print(f"[{p.name}] found {len(found)} accounts: {found}")
        except:
            pass
