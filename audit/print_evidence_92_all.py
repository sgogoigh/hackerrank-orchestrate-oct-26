import json

with open('dataset/evidence/records/service_resource_export_20260915_114455.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

for svc, exports in d.get('service_exports', {}).items():
    print(f"\nService: {svc}")
    for k, v in exports.items():
        print(f"  {k} ({len(v)} items):")
        for item in v:
            print(f"    {item}")
