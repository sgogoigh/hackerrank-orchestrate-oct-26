"""Inspects request_text across all 518 cases to identify non-deletion requests."""

import csv
import re
from pathlib import Path

def inspect_requests():
    with open("dataset/deletion_requests.csv", "r", encoding="utf-8") as f:
        cases = list(csv.DictReader(f))

    print(f"Total Cases: {len(cases)}")

    # Check request texts for non-deletion intents:
    # 1. Download / Export only without deletion
    # 2. Status check / inquiry only
    # 3. Cancel / withdraw deletion
    # 4. Rectification / update / correction only
    # 5. Access / lookup only

    non_deletion_keywords = [
        "do not delete", "don't delete", "cancel my deletion", "cancel deletion",
        "withdraw", "download my data", "export my data", "copy of my data",
        "access my data", "send me a copy", "rectify", "update my email",
        "password reset", "unsubscribe from marketing", "keep my account"
    ]

    suspicious = []
    for c in cases:
        txt = c["request_text"].lower()
        matched_kw = [kw for kw in non_deletion_keywords if kw in txt]
        if matched_kw:
            suspicious.append((c["case_id"], c["email"], matched_kw, c["request_text"]))

    print(f"\nSuspicious Non-Deletion Cases Found: {len(suspicious)}")
    for cid, em, kws, txt in suspicious[:20]:
        print(f"\n{cid} ({em}) - matched: {kws}")
        print(f"  {txt}")

if __name__ == "__main__":
    inspect_requests()
