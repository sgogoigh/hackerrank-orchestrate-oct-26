import csv
import json

with open("audit/test_eval_output.csv", "r", encoding="utf-8") as f:
    preds = {r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"])) for r in csv.DictReader(f)}

with open("dataset/sample_output.csv", "r", encoding="utf-8") as f:
    golds = {r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"])) for r in csv.DictReader(f)}

diff_cases = []
for cid in sorted(golds.keys()):
    p_stat, p_steps = preds[cid]
    g_stat, g_steps = golds[cid]
    if p_stat != g_stat or p_steps != g_steps:
        diff_cases.append((cid, p_stat, g_stat, p_steps, g_steps))

print(f"Total differing cases: {len(diff_cases)} / {len(golds)}")
for cid, p_stat, g_stat, p_steps, g_steps in diff_cases:
    print(f"\n--- {cid} (pred={p_stat}, gold={g_stat}) ---")
    if p_stat != g_stat:
        print(f"  Status mismatch!")
    
    p_keys = [(s.get('phase'), s.get('system_id'), s.get('resource_id'), s.get('operation'), s.get('state'), s.get('evidence_id')) for s in p_steps]
    g_keys = [(s.get('phase'), s.get('system_id'), s.get('resource_id'), s.get('operation'), s.get('state'), s.get('evidence_id')) for s in g_steps]
    
    missing = [k for k in g_keys if k not in p_keys]
    extra = [k for k in p_keys if k not in g_keys]
    if missing:
        print(f"  Missing steps ({len(missing)}): {missing}")
    if extra:
        print(f"  Extra steps ({len(extra)}): {extra}")
    if not missing and not extra:
        print(f"  Steps set matches, but ordering differs:")
        print(f"    Pred order: {[k[1:3] for k in p_keys]}")
        print(f"    Gold order: {[k[1:3] for k in g_keys]}")
