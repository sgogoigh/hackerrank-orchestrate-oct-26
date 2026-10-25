"""Refreshes dataset/cache/intent_cache.json deterministically across all cases."""

import csv
import json
from code.classifier import IntentClassifier

def refresh_cache():
    classifier = IntentClassifier()
    # Reset in-memory cache to re-evaluate with updated patterns
    classifier.cache = {}
    
    with open("dataset/deletion_requests.csv", "r", encoding="utf-8") as f:
        cases = list(csv.DictReader(f))

    non_dels = []
    for row in cases:
        cid = row["case_id"]
        txt = row["request_text"]
        is_del, intent = classifier.classify(cid, txt)
        if not is_del:
            non_dels.append((cid, intent, row["email"]))

    print(f"Re-classified {len(cases)} cases.")
    print(f"Total non-deletion detected: {len(non_dels)}")
    for cid, intent, em in non_dels:
        print(f"  {cid}: {intent} ({em})")

if __name__ == "__main__":
    refresh_cache()
