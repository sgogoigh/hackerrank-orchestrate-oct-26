import csv
from datetime import datetime

def parse_iso(ts):
    if not ts: return datetime.min
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

with open('dataset/sample_deletion_requests.csv', 'r', encoding='utf-8') as f:
    sample_cases = list(csv.DictReader(f))

with open('dataset/sample_output.csv', 'r', encoding='utf-8') as f:
    golds = {r['case_id']: r for r in csv.DictReader(f)}

with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    acts = list(csv.reader(f))[1:]

# Extract all account submissions
account_subs = [a for a in acts if a[3] == "deletion_worker" and a[4] == "account_service" and a[2] == "DELETE_RECORD"]

print(f"Total account submissions in system_activity: {len(account_subs)}")

# Match each sample case with nearby account submissions
for c in sample_cases:
    cid = c['case_id']
    rep_at = parse_iso(c['reported_at'])
    gold_steps = golds[cid]['steps_json']
    
    # Extract gold account_service steps
    import json
    g_steps = json.loads(gold_steps)
    gold_accs = [s['resource_id'] for s in g_steps if s['system_id'] == 'account_service']
    
    # Find matching account submissions in window [rep_at - 2h, rep_at]
    nearby = [a for a in account_subs if 0 <= (rep_at - parse_iso(a[1])).total_seconds() <= 7200]
    nearby_accs = [a[5] for a in nearby]
    
    print(f"{cid} (rep={c['reported_at']}): Gold account={gold_accs} | Nearby in activity={nearby_accs}")
