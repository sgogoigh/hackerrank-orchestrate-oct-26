"""Inspects all CLASSIFY_REQUEST rows in system_activity.csv and correlates with deletion_requests.csv."""

import csv

def inspect_classify_requests():
    with open("dataset/system_activity.csv", "r", encoding="utf-8") as f:
        acts = [r for r in csv.reader(f) if r and r[2] == "CLASSIFY_REQUEST"]

    print(f"Total CLASSIFY_REQUEST in system_activity.csv: {len(acts)}")

    with open("dataset/deletion_requests.csv", "r", encoding="utf-8") as f:
        requests = list(csv.DictReader(f))

    for a in acts:
        aid, ts, op, src, target, res_id, status, details = a
        print(f"\n{aid} ({ts}) res_id={res_id}: {details}")

        # Check if any request has reported_at near ts, or matches res_id
        # Let's search across requests for any request around this timestamp
        matches = [r for r in requests if abs((parse_iso(r["reported_at"]) - parse_iso(ts)).total_seconds()) <= 7200]
        for m in matches:
            print(f"   Potential case: {m['case_id']} ({m['email']}) req_at={m['requested_at']} rep_at={m['reported_at']}")
            print(f"   text: {m['request_text']}")

def parse_iso(ts):
    from datetime import datetime
    if not ts: return datetime.min
    return datetime.fromisoformat(ts.replace('Z', '+00:00'))

if __name__ == "__main__":
    inspect_classify_requests()
