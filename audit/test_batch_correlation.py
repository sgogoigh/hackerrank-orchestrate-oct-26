import csv
from datetime import datetime
import json

def parse_iso(ts):
    if not ts: return datetime.min
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

with open('dataset/sample_deletion_requests.csv', 'r', encoding='utf-8') as f:
    sample_cases = list(csv.DictReader(f))

with open('dataset/sample_output.csv', 'r', encoding='utf-8') as f:
    golds = {r['case_id']: r for r in csv.DictReader(f)}

with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    acts = list(csv.reader(f))[1:]

# All account submissions
acc_subs = [a for a in acts if a[3] == "deletion_worker" and a[4] == "account_service" and a[2] == "DELETE_RECORD"]

print("Analyzing sample cases for account_service and security_service verification...")
for c in sample_cases:
    cid = c['case_id']
    g_steps = json.loads(golds[cid]['steps_json'])
    g_acc = [s['resource_id'] for s in g_steps if s['system_id'] == 'account_service']
    g_sec = [s['resource_id'] for s in g_steps if s['system_id'] == 'security_service']
    
    rep_at = parse_iso(c['reported_at'])
    nearby_acc = [a[5] for a in acc_subs if 0 <= (rep_at - parse_iso(a[1])).total_seconds() <= 5400]
    
    print(f"{cid} (rep={c['reported_at']}): Gold acc={g_acc}, sec={g_sec} | Nearby acc={nearby_acc}")
