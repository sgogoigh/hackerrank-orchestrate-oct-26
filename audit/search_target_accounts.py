"""Check where account_5482, account_3866, account_7012 appear across the entire workspace."""

import csv
from pathlib import Path

target_accounts = ['account_5482', 'account_3866', 'account_7012', 'account_6440', 'account_410']

for p in Path('.').rglob('*'):
    if p.is_file() and p.suffix in ('.csv', '.json', '.sql', '.log', '.txt') and not str(p).startswith(('audit', '.git', 'output.csv', 'test_')):
        try:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                for a in target_accounts:
                    if a in content:
                        print(f"[{p}] has {a}")
        except:
            pass
