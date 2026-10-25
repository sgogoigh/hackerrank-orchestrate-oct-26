from pathlib import Path
import json

dataset_dir = Path("dataset")
records_dir = dataset_dir / "evidence" / "records"
user_to_audit_record = {}

for p in sorted(records_dir.glob("customer_data_snapshot_bundle_*.json")):
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        for s in data.get("snapshots", []):
            store = s.get("data_store")
            for r in s.get("records", []):
                rid = r.get("resource_id")
                cref = r.get("customer_reference") or r.get("subject_reference")
                if store == "security_service" and rid:
                    if cref:
                        user_to_audit_record[cref] = rid
                        if cref == "user_541":
                            print(f"Found user_541 in {p.name}: {rid}")
    except Exception as e:
        print(f"Error in {p}: {e}")

print("Direct test user_541:", user_to_audit_record.get('user_541'))
