"""Diagnostic and audit script for evaluating classification and sequence accuracy."""

import csv
import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from code.classifier import IntentClassifier
from code.evaluation.main import evaluate_predictions
from code.main import run_pipeline

def audit_classification_accuracy():
    """Checks intent classifier accuracy against ground truth in sample_output.csv."""
    sample_req_path = Path("dataset/sample_deletion_requests.csv")
    sample_out_path = Path("dataset/sample_output.csv")

    with open(sample_req_path, "r", encoding="utf-8") as f:
        requests = {r["case_id"]: r for r in csv.DictReader(f)}

    with open(sample_out_path, "r", encoding="utf-8") as f:
        golds = {r["case_id"]: r["deletion_status"] for r in csv.DictReader(f)}

    classifier = IntentClassifier()

    correct = 0
    total = len(requests)
    mismatches = []

    for cid, row in requests.items():
        text = row["request_text"]
        gold_status = golds[cid]
        gold_is_del = (gold_status != "NOT_APPLICABLE")
        pred_is_del = classifier.is_deletion_request(cid, text)

        if gold_is_del == pred_is_del:
            correct += 1
        else:
            mismatches.append((cid, text, gold_is_del, pred_is_del))

    accuracy = (correct / total) * 100.0
    print(f"=== CLASSIFICATION ACCURACY ===")
    print(f"Total Cases: {total}")
    print(f"Correct Intent Classifications: {correct} / {total} ({accuracy:.2f}%)")
    if mismatches:
        print("Mismatches found:")
        for cid, txt, g, p in mismatches:
            print(f"  {cid}: gold_is_del={g}, pred_is_del={p} | text: {txt[:80]}")
    else:
        print("All intent classifications match ground truth perfectly (100.0%)!")
    return accuracy

def audit_sequence_accuracy_details():
    """Detailed audit of sequence mismatches."""
    out_path = "audit/test_eval_output.csv"
    run_pipeline("dataset/sample_deletion_requests.csv", out_path)

    metrics = evaluate_predictions(out_path, "dataset/sample_output.csv")
    print("\n=== PIPELINE METRICS ===")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    with open(out_path, "r", encoding="utf-8") as f:
        preds = {r["case_id"]: json.loads(r["steps_json"]) for r in csv.DictReader(f)}

    with open("dataset/sample_output.csv", "r", encoding="utf-8") as f:
        golds = {r["case_id"]: json.loads(r["steps_json"]) for r in csv.DictReader(f)}

    print("\n=== SEQUENCE FAILURE ANALYSIS ===")
    for cid in sorted(golds.keys()):
        p_steps = preds[cid]
        g_steps = golds[cid]
        if p_steps != g_steps:
            print(f"\n--- {cid} ---")
            print(f"Pred steps ({len(p_steps)}):")
            for s in p_steps:
                print(f"   [{s.get('phase')}] {s.get('system_id')}.{s.get('resource_id')} -> {s.get('operation')} ({s.get('state')}) ev='{s.get('evidence_id')}'")
            print(f"Gold steps ({len(g_steps)}):")
            for s in g_steps:
                print(f"   [{s.get('phase')}] {s.get('system_id')}.{s.get('resource_id')} -> {s.get('operation')} ({s.get('state')}) ev='{s.get('evidence_id')}'")

if __name__ == "__main__":
    audit_classification_accuracy()
    audit_sequence_accuracy_details()
