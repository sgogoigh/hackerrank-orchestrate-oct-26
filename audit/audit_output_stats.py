"""Audits distribution and characteristics of output.csv."""

import csv
from collections import Counter

def audit_output_file(path="output.csv"):
    with open(path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    print(f"=== AUDIT OF {path} ===")
    print(f"Total Rows: {len(reader)}")

    status_counts = Counter(r["deletion_status"] for r in reader)
    print("\nDeletion Status Distribution:")
    for status, count in status_counts.most_common():
        pct = (count / len(reader)) * 100.0
        print(f"  {status}: {count} ({pct:.2f}%)")

if __name__ == "__main__":
    audit_output_file("output.csv")
