import json

with open('dataset/evidence/records/customer_data_snapshot_bundle_20260915.json', 'r', encoding='utf-8') as f:
    bundle = json.load(f)

for s in bundle.get('snapshots', []):
    store = s.get('data_store')
    coll = s.get('collection')
    recs = s.get('records', [])
    for r in recs:
        cref = r.get('customer_reference') or r.get('subject_reference')
        if cref in ('user_31', 'user_32'):
            print(f"[{store}.{coll}] cref={cref} rec={r}")
