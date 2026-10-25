import csv
import json

with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    acts = list(csv.DictReader(f))

anons = [a for a in acts if a['event_type'] == 'ANONYMIZE_RECORD']
print(f"Total ANONYMIZE_RECORD events: {len(anons)}")
for a in anons:
    print(f"  {a['event_time']} | {a['target_system']} | {a['resource_id']} | {a['details']}")
