import glob
import re

for f in sorted(glob.glob('dataset/evidence/databases/*.sql'))[:5]:
    print('File:', f)
    count = 0
    for line in open(f, encoding='utf-8', errors='ignore'):
        if line.startswith('INSERT INTO'):
            print('  Line:', line[:120])
            count += 1
            if count >= 2:
                break
