# Evaluation Report - Ghost Data Still Exists

## 1. Executive Summary & Benchmark Metrics

This report summarizes the performance of the AI-powered deletion-audit agent against the reference golden dataset (`sample_output.csv`).

| Metric Category | Metric Name | Score |
|---|---|---|
| **Case Level** | Deletion Status Accuracy | 100.00% |
| **Sequence Level** | Exact Array Sequence Accuracy | 37.50% |
| **Step Level** | Step Precision | 96.25% |
| **Step Level** | Step Recall | 79.79% |
| **Step Level** | Step F1-Score | 87.25% |
| **Field Accuracy** | `phase` Accuracy | 96.25% |
| **Field Accuracy** | `system_id` Accuracy | 71.25% |
| **Field Accuracy** | `resource_id` Accuracy | 71.25% |
| **Field Accuracy** | `operation` Accuracy | 71.88% |
| **Field Accuracy** | `state` Accuracy | 74.38% |
| **Field Accuracy** | `evidence_id` Accuracy | 98.75% |

---

## 2. Participant-Created Evaluation Test Cases

### Case 1: Decoy Identity Collisions in Secondary Replicas
* **Context:** A user whose name is partially shared by decoy accounts in regional read replicas.
* **Ground Truth:** The auditor must resolve exact internal `user_id` and SHA-256 email hashes, ignoring decoy accounts (`account_8741`, `account_9116`) that belong to other users.
* **Outcome:** Clean verification isolating only the target subject's records.

### Case 2: Multi-Hop Historical Alias Resolution
* **Context:** A customer changed their email address twice in `user_audit_log.csv` before requesting deletion using their original email.
* **Ground Truth:** The agent successfully chains `user_audit_log` records to associate all three addresses with the stable `user_id`, finding a residual log entry in `support_replica.log`.
* **Outcome:** Detected `REPORT_EXPOSED_PII` on the support ticket with proper remediation.

### Case 3: Retained Security Audit Log vs. Active Restore Risk
* **Context:** A deletion request where the primary account was purged, but a backup archive had `restore_allowed = true` while a legal hold audit log was active.
* **Ground Truth:** Emits `REPORT_RESTORE_RISK` and `BLOCK_RESTORE` for the backup, while retaining `VERIFY_RECORD_PRESENT` for the security record.
* **Outcome:** Complies with `rule_12` (retain security logs) and `rule_14` (block restore path).

---

## 3. Failures Found and Improvements Made

1. **Failure Found:** Replicas exhibiting false `COMPLETE` claims due to asynchronous synchronization lag.
   - **Improvement:** Implemented a direct SQL and readback log parser that cross-verifies replica state rather than accepting `reported_status`.
2. **Failure Found:** Non-deletion requests (marketing opt-out) incorrectly undergoing system audits.
   - **Improvement:** Added Filter 1 (`code/classifier.py`) powered by Gemini 3.8 Flash, routing non-deletion requests immediately to `NOT_APPLICABLE` with `steps_json = []`.
3. **Failure Found:** Step ordering discrepancies between phases and operations.
   - **Improvement:** Added deterministic weighted sorting enforcing `FINDING` -> `REMEDIATION` -> `VERIFICATION` and operation hierarchy.
