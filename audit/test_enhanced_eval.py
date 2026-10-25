"""Test evaluation metrics with full associations."""

import csv
import json
from code.identity import IdentityResolver, SubjectIdentity
from code.evidence_scanner import EvidenceScanner, ObservedResource
from code.auditor import DeletionAuditor
from code.evaluation.main import evaluate_predictions

# Run evaluation on sample_deletion_requests.csv
resolver = IdentityResolver()
scanner = EvidenceScanner()
auditor = DeletionAuditor()

with open("dataset/sample_deletion_requests.csv", "r", encoding="utf-8") as f:
    sample_cases = list(csv.DictReader(f))

preds = []
for row in sample_cases:
    case_id = row["case_id"].strip()
    email = row["email"].strip()
    audit_at = row["audit_at"].strip()
    requested_at = row.get("requested_at", "").strip()
    request_text = row.get("request_text", "").strip()
    
    # 1. Classification
    from code.classifier import IntentClassifier
    classifier = IntentClassifier(cache_path="dataset/cache/intent_cache.json")
    is_deletion = classifier.is_deletion_request(case_id, request_text)
    if not is_deletion:
        preds.append((case_id, "NOT_APPLICABLE", "[]"))
        continue
        
    identity = resolver.resolve(email)
    if not identity:
        preds.append((case_id, "NOT_APPLICABLE", "[]"))
        continue
        
    resources = scanner.scan_subject_resources(
        identity=identity,
        audit_at=audit_at,
        requested_at=requested_at,
        case_id=case_id,
    )
    
    status, steps = auditor.audit_case(case_id, is_deletion, resources, identity=identity)
    preds.append((case_id, status, json.dumps(steps, separators=(",", ":"), ensure_ascii=False)))

# Write to test_eval_output.csv
with open("audit/test_eval_output.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["case_id", "deletion_status", "steps_json"])
    for cid, st, sj in preds:
        writer.writerow([cid, st, sj])

# Evaluate
results = evaluate_predictions("audit/test_eval_output.csv", "dataset/sample_output.csv")
print("=== ITERATION 7 TEST EVALUATION RESULTS ===")
for k, v in results.items():
    print(f"  {k}: {v}")
