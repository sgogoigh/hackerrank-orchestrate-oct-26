"""Investigate the exact verification steps missing in the 14 cases."""

import csv
import json

with open("audit/test_eval_output.csv", "r", encoding="utf-8") as f:
    preds = {r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"])) for r in csv.DictReader(f)}

with open("dataset/sample_output.csv", "r", encoding="utf-8") as f:
    golds = {r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"])) for r in csv.DictReader(f)}

target_cases = ['case_09', 'case_18', 'case_20', 'case_21', 'case_22', 'case_23', 'case_25', 'case_26', 'case_27', 'case_28', 'case_29', 'case_30', 'case_31', 'case_32']

print(f"Investigating {len(target_cases)} cases:")
for cid in target_cases:
    p_stat, p_steps = preds[cid]
    g_stat, g_steps = golds[cid]
    
    # Compare verification phase steps
    p_verif = [s for s in p_steps if s['phase'] == 'VERIFICATION']
    g_verif = [s for s in g_steps if s['phase'] == 'VERIFICATION']
    
    p_keys = set((s['system_id'], s['resource_id'], s['operation'], s['evidence_id']) for s in p_verif)
    g_keys = set((s['system_id'], s['resource_id'], s['operation'], s['evidence_id']) for s in g_verif)
    
    missing_in_pred = g_keys - p_keys
    extra_in_pred = p_keys - g_keys
    
    print(f"\n{cid} ({g_stat}):")
    print(f"  Missing in pred: {missing_in_pred}")
    print(f"  Extra in pred:   {extra_in_pred}")
