"""Breakdown of sequence mismatches into precise categories."""

import csv
import json

with open("audit/test_eval_output.csv", "r", encoding="utf-8") as f:
    preds = {r["case_id"]: json.loads(r["steps_json"]) for r in csv.DictReader(f)}

with open("dataset/sample_output.csv", "r", encoding="utf-8") as f:
    golds = {r["case_id"]: json.loads(r["steps_json"]) for r in csv.DictReader(f)}

# Categorize:
# 1. Missing account_service verification
# 2. Missing security_service verification
# 3. Step ordering difference (same set of steps, different order)
# 4. Other missing/extra steps

missing_acct = []
missing_sec = []
order_diff = []
other = []

for cid in sorted(golds.keys()):
    p_steps = preds[cid]
    g_steps = golds[cid]
    if p_steps == g_steps:
        continue

    p_tuples = [(s.get("phase"), s.get("system_id"), s.get("resource_id"), s.get("operation"), s.get("evidence_id")) for s in p_steps]
    g_tuples = [(s.get("phase"), s.get("system_id"), s.get("resource_id"), s.get("operation"), s.get("evidence_id")) for s in g_steps]

    p_set = set(p_tuples)
    g_set = set(g_tuples)

    miss = g_set - p_set
    extra = p_set - g_set

    # Check what is in miss
    has_acct_miss = any(m[1] == "account_service" for m in miss)
    has_sec_miss = any(m[1] == "security_service" for m in miss)

    if sorted(p_tuples) == sorted(g_tuples):
        order_diff.append(cid)
    elif has_acct_miss and not extra:
        missing_acct.append((cid, miss))
    else:
        other.append((cid, miss, extra))

print(f"Total Mismatches: {len(missing_acct) + len(order_diff) + len(other)} / {len(golds)}")
print(f"Order differences only: {len(order_diff)} cases: {order_diff}")
print(f"Missing account/sec verification only: {len(missing_acct)} cases: {[c[0] for c in missing_acct]}")
print(f"Other differences: {len(other)} cases: {[c[0] for c in other]}")

print("\n--- Details of Other differences ---")
for cid, miss, extra in other:
    print(f"\n{cid}:")
    print(f"  MISS ({len(miss)}): {list(miss)}")
    print(f"  EXTRA ({len(extra)}): {list(extra)}")
