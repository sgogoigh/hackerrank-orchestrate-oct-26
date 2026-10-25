"""Examine how cases map to system_activity.csv records."""

import csv
from datetime import datetime

def parse_iso(ts):
    if not ts: return datetime.min
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

with open("dataset/sample_deletion_requests.csv", "r", encoding="utf-8") as f:
    sample_requests = list(csv.DictReader(f))

with open("dataset/sample_output.csv", "r", encoding="utf-8") as f:
    sample_outputs = {r["case_id"]: r for r in csv.DictReader(f)}

with open("dataset/system_activity.csv", "r", encoding="utf-8") as f:
    activities = list(csv.reader(f))[1:]

del_acts = [a for a in activities if a[3] == "deletion_worker"]

print("Analyzing sample cases against deletion worker batches...")
for req in sample_requests[20:30]:
    cid = req["case_id"]
    em = req["email"]
    req_at = req["requested_at"]
    rep_at = req["reported_at"]
    aud_at = req["audit_at"]
    t_rep = parse_iso(rep_at)

    gold = sample_outputs[cid]
    print(f"\n================ {cid} ({em}) ================")
    print(f"requested_at: {req_at} | reported_at: {rep_at}")
    print(f"Gold steps: {gold['steps_json']}")

    # Find del_acts within 2 hours before reported_at
    nearby = [a for a in del_acts if 0 <= (t_rep - parse_iso(a[1])).total_seconds() <= 7200]
    print(f"Nearby deletion_worker activities ({len(nearby)}):")
    for a in nearby:
        print(f"   {a[1]} | {a[2]} | {a[4]} | {a[5]} | {a[6]} | {a[7]}")
