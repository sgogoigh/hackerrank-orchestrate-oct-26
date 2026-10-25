import csv
from datetime import datetime

def parse_iso(ts):
    if not ts: return datetime.min
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

with open('dataset/sample_deletion_requests.csv', 'r', encoding='utf-8') as f:
    sample_cases = list(csv.DictReader(f))

with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    acts = list(csv.reader(f))[1:]

for c in sample_cases[20:30]:
    cid = c['case_id']
    em = c['email']
    rep_at = parse_iso(c['reported_at'])
    print(f"\n==================== {cid} ({em}) rep_at={c['reported_at']} ====================")
    # Check all activities within [rep_at - 1.5 hours, rep_at]
    batch = [a for a in acts if 0 <= (rep_at - parse_iso(a[1])).total_seconds() <= 5400]
    for b in batch:
        print(f"  {b[1]} | {b[2]} | {b[3]} | {b[4]} | {b[5]} | {b[6]} | {b[7]}")
