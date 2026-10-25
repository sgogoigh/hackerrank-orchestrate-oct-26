"""Examine customer_data_snapshot_bundle_20260917.json snapshots structure."""

import json

with open("dataset/evidence/records/customer_data_snapshot_bundle_20260917.json", "r", encoding="utf-8") as f:
    bundle = json.load(f)

print("Bundle top-level keys:", bundle.keys())
print("Bundle captured_at:", bundle.get("captured_at"))
snapshots = bundle.get("snapshots", [])
print(f"Total snapshot collections: {len(snapshots)}")

for s in snapshots:
    store = s.get("data_store")
    coll = s.get("collection")
    cap = s.get("captured_at")
    recs = s.get("records", [])
    print(f"Collection: store={store}, coll={coll}, captured_at={cap}, record_count={len(recs)}")
    if recs:
        print(f"   First record sample: {recs[0]}")
