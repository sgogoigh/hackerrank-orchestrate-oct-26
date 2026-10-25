import json

with open('dataset/evidence/records/customer_data_snapshot_bundle_20260915.json', 'r', encoding='utf-8') as f:
    bundle = json.load(f)

for s in bundle.get('snapshots', []):
    store = s.get('data_store')
    coll = s.get('collection')
    recs = s.get('records', [])
    print(f"[{store}.{coll}] records={len(recs)}")
    for r in recs[:2]:
        print(f"   sample: {r}")
