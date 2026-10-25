import csv
import json
from datetime import datetime

def parse_iso(ts):
    if not ts: return datetime.min
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

with open('dataset/sample_deletion_requests.csv', 'r', encoding='utf-8') as f:
    sample_cases = list(csv.DictReader(f))

with open('dataset/sample_output.csv', 'r', encoding='utf-8') as f:
    golds = {r['case_id']: json.loads(r['steps_json']) for r in csv.DictReader(f)}

with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    acts = list(csv.DictReader(f))

worker_acts = [a for a in acts if a['source_system'] == 'deletion_worker']

# Group cases by reported_at
cases_by_rep = {}
for c in sample_cases:
    cases_by_rep.setdefault(c['reported_at'], []).append(c)

for rep_at, clist in sorted(cases_by_rep.items()):
    t_rep = parse_iso(rep_at)
    b_acts = [a for a in worker_acts if 0 <= (t_rep - parse_iso(a['event_time'])).total_seconds() <= 5400]
    
    print(f"\n==================== Batch {rep_at} ({len(clist)} cases, {len(b_acts)} worker acts) ====================")
    for c in clist:
        cid = c['case_id']
        g_steps = golds[cid]
        g_res = [(s['system_id'], s['resource_id'], s['operation']) for s in g_steps]
        print(f"  {cid} ({c['email']}):")
        print(f"    Gold: {g_res}")
    
    b_res = [(a['target_system'], a['resource_id'], a['event_type'], a['reported_result']) for a in b_acts]
    print(f"  Batch activities: {b_res}")
