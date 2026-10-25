import csv
from datetime import datetime

def parse_iso(ts):
    if not ts: return datetime.min
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

with open('dataset/deletion_requests.csv', 'r', encoding='utf-8') as f:
    cases = list(csv.DictReader(f))

with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    acts = list(csv.DictReader(f))

worker_acts = [a for a in acts if a['source_system'] == 'deletion_worker']

print(f"Total deletion requests: {len(cases)}")
print(f"Total deletion worker activities: {len(worker_acts)}")

# Group cases by reported_at
cases_by_rep = {}
for c in cases:
    cases_by_rep.setdefault(c['reported_at'], []).append(c)

print(f"Distinct reported_at timestamps: {len(cases_by_rep)}")

# Check matching worker acts for each reported_at
matched_batches = 0
unmatched_batches = 0

for rep_at, clist in cases_by_rep.items():
    t_rep = parse_iso(rep_at)
    batch_acts = [a for a in worker_acts if 0 <= (t_rep - parse_iso(a['event_time'])).total_seconds() <= 5400]
    if batch_acts:
        matched_batches += 1
    else:
        unmatched_batches += 1

print(f"Matched batches: {matched_batches}, Unmatched: {unmatched_batches}")
