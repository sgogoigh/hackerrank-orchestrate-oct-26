from pathlib import Path

targets = ['account_5482', 'account_7012', 'account_3866', 'account_3136', 'account_5684', 'account_6440']

for p in Path('dataset').rglob('*'):
    if p.is_file() and p.suffix in ('.csv', '.json', '.sql', '.log', '.txt'):
        try:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                for t in targets:
                    if t in content:
                        print(f"Found {t} in {p}")
        except:
            pass
