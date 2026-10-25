import re
import csv

non_deletion_patterns = [
    r"don'?t delete",
    r"do not delete",
    r"do not close",
    r"don'?t close",
    r"not (asking for|a request for|a request to) (deletion|erase|delete)",
    r"leave the account active",
    r"leave my (profile|account|records|purchase history)",
    r"keep the account",
    r"without removing any of my records",
    r"marketing lists? only",
    r"stop the promotional emails",
    r"continue using the service",
    r"i still (use|need) (it|the account)",
    r"this is an information request",
]

def is_non_del(text):
    cleaned = text.strip().lower()
    for pat in non_deletion_patterns:
        if re.search(pat, cleaned):
            return True, pat
    return False, None

with open('dataset/deletion_requests.csv', 'r', encoding='utf-8') as f:
    cases = list(csv.DictReader(f))

with open('dataset/sample_deletion_requests.csv', 'r', encoding='utf-8') as f:
    sample_cases = list(csv.DictReader(f))

found_non_del = []
for c in cases:
    is_nd, pat = is_non_del(c['request_text'])
    if is_nd:
        found_non_del.append((c['case_id'], c['email'], pat, c['request_text']))

sample_non_del = [c['case_id'] for c in sample_cases if is_non_del(c['request_text'])[0]]

print(f"Total Non-Deletion Requests Identified across 518 cases: {len(found_non_del)}")
print(f"Total Non-Deletion in sample (32 cases): {len(sample_non_del)}")
for cid, em, pat, txt in found_non_del:
    print(f"  {cid} ({em}) [pat={pat}]: {txt}")
