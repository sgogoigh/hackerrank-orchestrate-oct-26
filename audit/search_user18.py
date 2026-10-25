from pathlib import Path

for p in Path('dataset/evidence').rglob('*'):
    if p.is_file():
        try:
            c = open(p, 'r', encoding='utf-8', errors='ignore').read()
            if 'user_18' in c:
                print(f"user_18 in {p}")
            if 'user_20' in c:
                print(f"user_20 in {p}")
        except:
            pass
