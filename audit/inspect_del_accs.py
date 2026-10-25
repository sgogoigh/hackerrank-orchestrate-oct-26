import csv
import json

with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    acts = list(csv.DictReader(f))

# Let's inspect all DELETE_RECORD for account_service and ANONYMIZE_RECORD for analytics_platform
del_accs = [a for a in acts if a['source_system'] == 'deletion_worker' and a['target_system'] == 'account_service' and a['event_type'] == 'DELETE_RECORD']
anon_anas = [a for a in acts if a['source_system'] == 'deletion_worker' and a['target_system'] == 'analytics_platform' and a['event_type'] == 'ANONYMIZE_RECORD']

print(f"Total DELETE_RECORD accounts: {len(del_accs)}")
print(f"Total ANONYMIZE_RECORD analytics: {len(anon_anas)}")

# Look at details of del_accs
for a in del_accs[:10]:
    print(f"  {a['event_time']} | {a['resource_id']} | {a['details']}")
