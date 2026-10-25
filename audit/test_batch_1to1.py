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

# All account submissions
acc_subs = [a for a in acts if a['source_system'] == 'deletion_worker' and a['target_system'] == 'account_service' and a['event_type'] == 'DELETE_RECORD']

# Group sample cases by reported_at
by_rep = {}
for c in sample_cases:
    by_rep.setdefault(c['reported_at'], []).append(c)

matches = 0
total_checked = 0

for rep_at, cases in by_rep.items():
    t_rep = parse_iso(rep_at)
    # Find matching account submissions in [rep_at - 1.5h, rep_at]
    batch_accs = [a for a in acc_subs if 0 <= (t_rep - parse_iso(a['event_time'])).total_seconds() <= 5400]
    batch_accs.sort(key=lambda a: a['event_time'])
    
    # Sort cases by case_id / user_id
    cases.sort(key=lambda c: int(c['case_id'].split('_')[1]))
    
    for i, c in enumerate(cases):
        cid = c['case_id']
        g_steps = json.loads(golds[cid]['steps_json'])
        g_acc = [s['resource_id'] for s in g_steps if s['system_id'] == 'account_service']
        
        # Check if 1-to-1 match or direct match
        pred_acc = None
        if i < len(batch_accs):
            pred_acc = batch_accs[i]['resource_id']
            
        is_m = bool(g_acc and pred_acc in g_acc)
        if is_m: matches += 1
        total_checked += 1
        print(f"{cid} (rep={rep_at}): Gold={g_acc} | Matched={pred_acc} -> {'MATCH' if is_m else 'DIFF'}")

print(f"\nTotal 1-to-1 Batch Account Matches: {matches} / {total_checked}")
