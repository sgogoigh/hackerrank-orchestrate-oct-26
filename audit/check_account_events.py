import csv

with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    acts = list(csv.DictReader(f))

targets = ['account_5521', 'account_5037', 'account_4990', 'account_994', 'account_7012', 'account_4163', 'account_4857', 'account_8858', 'account_6440', 'account_410', 'account_3136', 'account_5482']

for a in acts:
    for t in targets:
        if t in a['resource_id'] or t in a['details']:
            print(f"[{a['event_time']}] act={a['activity_id']} type={a['event_type']} src={a['source_system']} tgt={a['target_system']} res={a['resource_id']} st={a['reported_result']} | det={a['details']}")
