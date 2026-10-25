import json
import glob
for p in sorted(glob.glob('dataset/evidence/records/customer_data_snapshot_bundle_*.json')):
    d = json.load(open(p, encoding='utf-8'))
    for s in d.get('snapshots', []):
        for r in s.get('records', []):
            if r.get('subject_reference') == 'user_541' or r.get('customer_reference') == 'user_541':
                print(p, s.get('data_store'), r)
