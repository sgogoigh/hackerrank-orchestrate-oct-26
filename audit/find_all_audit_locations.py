from pathlib import Path

targets = ['audit_record_4902', 'audit_record_6645', 'audit_record_5569', 'audit_record_4128', 'audit_record_3954', 'audit_record_1707']

for p in Path('dataset').rglob('*'):
    if p.is_file() and p.suffix in ('.csv', '.json', '.sql', '.log', '.txt'):
        try:
            c = open(p, 'r', encoding='utf-8', errors='ignore').read()
            for t in targets:
                if t in c:
                    print(f"[{p.name}] has {t}")
        except:
            pass
