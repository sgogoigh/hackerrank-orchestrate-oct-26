import json

d = json.load(open('dataset/evidence/records/service_resource_export_20260915_114455.json', 'r', encoding='utf-8'))
print('=== profile_lookups ===')
for x in d['service_exports']['account_service']['profile_lookups']:
    print(x)
print('\n=== audit_records ===')
for x in d['service_exports']['security_service']['audit_records']:
    print(x)
print('\n=== profiles ===')
for x in d['service_exports']['analytics_platform']['profiles']:
    print(x)
