from pathlib import Path

for p in Path('.').rglob('*'):
    if p.is_file() and p.suffix in ('.csv', '.json', '.sql', '.log', '.txt') and not str(p).startswith(('audit', '.git', 'output.csv', 'test_')):
        try:
            c = open(p, 'r', encoding='utf-8', errors='ignore').read()
            if 'account_4857' in c: print('4857 in', p)
            if 'account_8858' in c: print('8858 in', p)
        except: pass
