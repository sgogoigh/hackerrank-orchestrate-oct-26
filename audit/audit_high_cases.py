"""Inspects all cases from case_500 onwards in deletion_requests.csv."""

import csv

def inspect_high_cases():
    with open("dataset/deletion_requests.csv", "r", encoding="utf-8") as f:
        cases = [r for r in csv.DictReader(f)]

    high_cases = [c for c in cases if int(c["case_id"].split("_")[1]) >= 500]
    print(f"Total cases >= 500: {len(high_cases)}")

    for c in high_cases:
        print(f"\n{c['case_id']} ({c['email']}) req_at={c['requested_at']} rep_at={c['reported_at']}")
        print(f"  {c['request_text'].encode('ascii', errors='backslashreplace').decode('ascii')}")

if __name__ == "__main__":
    inspect_high_cases()
