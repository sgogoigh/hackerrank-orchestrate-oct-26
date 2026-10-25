import glob
import re

for f in sorted(glob.glob('dataset/evidence/databases/*.sql')):
    tables = set()
    sample_insert = None
    for line in open(f, encoding='utf-8', errors='ignore'):
        m = re.match(r'INSERT INTO "?(\w+)"?\s+VALUES\s*\((.*)\);', line.strip())
        if m:
            tables.add(m.group(1))
            if not sample_insert:
                sample_insert = line.strip()[:100]
    print(f"{f}: tables={tables}")
    if sample_insert:
        print(f"   sample: {sample_insert}")
