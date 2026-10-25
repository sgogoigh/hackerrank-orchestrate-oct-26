import json

with open('dataset/evidence/records/customer_data_snapshot_bundle_20260917.json', 'r', encoding='utf-8') as f:
    bundle = json.load(f)

print(f"Top-level keys in bundle_92: {list(bundle.keys())}")
print(f"Number of snapshots: {len(bundle.get('snapshots', []))}")
for i, s in enumerate(bundle.get('snapshots', [])):
    ds = s.get('data_store')
    cap = s.get('captured_at')
    recs = s.get('records', [])
    print(f"Snapshot {i}: data_store={ds}, captured_at={cap}, record_count={len(recs)}")
    for r in recs[:2]:
        print(f"   sample: {r}")

print("\nService exports:")
for k, v in bundle.get('service_exports', {}).items():
    print(f"  Export: {k}, keys={list(v.keys())}")
    for subk, subv in v.items():
        print(f"    {subk}: len={len(subv)}, sample={subv[:1]}")
