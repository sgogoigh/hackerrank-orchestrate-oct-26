"""Inspect contents of service_resource_export_20260915_114455.json (evidence_92)."""

import json

with open("dataset/evidence/records/service_resource_export_20260915_114455.json", "r", encoding="utf-8") as f:
    d = json.load(f)

for svc, content in d.get("service_exports", {}).items():
    print(f"\n--- {svc} ---")
    if isinstance(content, dict):
        for k, v in content.items():
            if isinstance(v, list):
                print(f"  key: {k} (list of {len(v)} items)")
                if v:
                    print(f"     first item sample: {v[0]}")
            else:
                print(f"  key: {k}: {type(v)}")
    elif isinstance(content, list):
        print(f"  list of {len(content)} items")
        if content:
            print(f"     first item sample: {content[0]}")
