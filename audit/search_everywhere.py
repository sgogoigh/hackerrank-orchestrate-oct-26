from pathlib import Path

for p in Path('.').rglob('*'):
    if p.is_file() and not str(p).startswith(('.git', 'audit', 'output.csv')):
        try:
            c = open(p, 'r', encoding='utf-8', errors='ignore').read()
            if '6645' in c:
                print(f"6645 in {p}")
            if '5569' in c:
                print(f"5569 in {p}")
        except:
            pass
