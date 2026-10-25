from pathlib import Path

for p in Path('dataset').rglob('*'):
    if p.is_file():
        try:
            c = open(p, 'r', encoding='utf-8', errors='ignore').read()
            if '6645' in c:
                print(f"6645 in {p}")
        except:
            pass
