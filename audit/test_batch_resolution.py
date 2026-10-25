"""Test batch correlation of resources to cases."""

import csv
import json
from datetime import datetime

def parse_iso(ts):
    if not ts: return datetime.min
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

with open('dataset/sample_deletion_requests.csv', 'r', encoding='utf-8') as f:
    sample_cases = list(csv.DictReader(f))

with open('dataset/sample_output.csv', 'r', encoding='utf-8') as f:
    golds = {r['case_id']: r for r in csv.DictReader(f)}

with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    acts = list(csv.DictReader(f))

# Group cases by reported_at
cases_by_rep = {}
for c in sample_cases:
    cases_by_rep.setdefault(c['reported_at'], []).append(c)

for rep_at, cases in cases_by_rep.items():
    t_rep = parse_iso(rep_at)
    batch_acts = [a for a in acts if a['source_system'] == 'deletion_worker' and 0 <= (t_rep - parse_iso(a['event_time'])).total_seconds() <= 5400]
    
    acc_acts = [a['resource_id'] for a in batch_acts if a['target_system'] == 'account_service' and a['event_type'] == 'DELETE_RECORD']
    ana_acts = [a['resource_id'] for a in batch_acts if a['target_system'] == 'analytics_platform' and a['event_type'] == 'ANONYMIZE_RECORD']
    
    print(f"\nBatch rep_at={rep_at} (cases={len(cases)}):")
    for i, c in enumerate(cases):
        cid = c['case_id']
        g_steps = json.loads(golds[cid]['steps_json'])
        g_acc = [s['resource_id'] for s in g_steps if s['system_id'] == 'account_service']
        g_ana = [s['resource_id'] for s in g_steps if s['system_id'] == 'analytics_platform']
        print(f"  {cid} ({c['email']}): Gold acc={g_acc}, ana={g_ana}")
    print(f"  Batch acc={acc_acts}")
    print(f"  Batch ana={ana_acts}")
