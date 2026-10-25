from pathlib import Path

targets = ['account_3960', 'account_5521', 'account_5037', 'account_4990', 'account_410', 'account_7012', 'account_4163', 'account_4857', 'account_8858']

for p in Path('dataset').rglob('*'):
    if p.is_file() and p.suffix in ('.log', '.json', '.sql', '.txt'):
        try:
            c = open(p, 'r', encoding='utf-8', errors='ignore').read()
            for t in targets:
                if t in c:
                    print(f"[{p.name}] has {t}")
        except:
            pass
