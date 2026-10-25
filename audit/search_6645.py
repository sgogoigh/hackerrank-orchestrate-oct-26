from pathlib import Path

for p in Path('dataset').rglob('*'):
    if p.is_file():
        try:
            c = open(p, 'r', encoding='utf-8', errors='ignore').read()
            if 'audit_record_6645' in c:
                print(f"6645 in {p}")
            if 'audit_record_5569' in c:
                print(f"5569 in {p}")
        except:
            pass
