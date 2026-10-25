import csv
import json
from datetime import datetime

def parse_iso(ts):
    if not ts: return datetime.min
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

with open('dataset/sample_deletion_requests.csv', 'r', encoding='utf-8') as f:
    cases = list(csv.DictReader(f))

with open('dataset/sample_output.csv', 'r', encoding='utf-8') as f:
    golds = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}

with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    acts = list(csv.DictReader(f))

# Look at deletion_worker activities
worker_acts = [a for a in acts if a['source_system'] == 'deletion_worker']

print(f"Total cases: {len(cases)}, Total worker activities: {len(worker_acts)}")

# For each case, check worker activities between requested_at and reported_at
for c in cases:
    cid = c['case_id']
    req_at = parse_iso(c.get('requested_at', ''))
    rep_at = parse_iso(c.get('reported_at', ''))
    
    # Gold resources
    g_stat, g_steps = golds[cid]
    g_resources = set((s['system_id'], s['resource_id']) for s in g_steps)
    
    # Activities between req_at and rep_at + 1 hour
    relevant_acts = []
    for a in worker_acts:
        t = parse_iso(a['event_time'])
        # If event is within window [req_at - 1h, rep_at + 1h]
        if req_at <= t <= rep_at:
            relevant_acts.append((a['target_system'], a['resource_id'], a['event_type'], a['reported_result']))
            
    print(f"\n{cid} ({c['email']}) [req={c.get('requested_at')} -> rep={c.get('reported_at')}]:")
    print(f"  Gold resources: {sorted(list(g_resources))}")
    print(f"  Worker acts in window: {relevant_acts}")
