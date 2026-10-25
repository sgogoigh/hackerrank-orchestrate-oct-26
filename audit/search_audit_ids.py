from pathlib import Path

targets = ['6645', '5569', '8486', '5080']

for p in Path('dataset/evidence').rglob('*'):
    if p.is_file():
        try:
            c = open(p, 'r', encoding='utf-8', errors='ignore').read()
            for t in targets:
                if f'audit_record_{t}' in c:
                    print(f"audit_record_{t} in {p}")
        except:
            pass
