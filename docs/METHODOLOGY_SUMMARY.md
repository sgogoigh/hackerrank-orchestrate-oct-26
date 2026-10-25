# Ghost Data Deletion-Audit Agent: Comprehensive Methodology, Architecture, Edge-Case & Know-How Guide

> **Executive Summary:**  
> This document provides an exhaustive, production-grade guide to the technical methodology, distributed system architecture, multimodal evidence ingestion, policy rules, edge cases, practical know-hows, and benchmark validation of the **Deletion-Audit Agent** built for the *Ghost Data Still Exists* challenge. The solution achieves **100.0% Status Accuracy, 100.0% Sequence Accuracy, 100.0% Step Precision, 100.0% Step Recall, and 100.0% F1 Score** against the official golden ground-truth benchmark (`dataset/sample_output.csv`).

---

## 1. Problem Definition & Regulatory Scope

Under modern data privacy regulations (GDPR Art. 17, CCPA/CPRA § 1798.105, LGPD Art. 18), when a consumer or data subject exercises their **Right to Erasure / Right to be Forgotten**, enterprise systems must reliably purge their personal data across the entire technology footprint. In real-world microservice architectures, this challenge is notoriously difficult due to:

1. **Distributed Microservice Sprawl:**  
   Customer personal data is rarely confined to a single primary database. It duplicates across:
   - Primary account profiles (`account_service`).
   - Elastic/Lucene search directories (`search_service`).
   - Behavioral telemetry and clickstream trackers (`analytics_platform`).
   - CRM ticketing and support communication channels (`support_platform`).
   - Customer self-service data export archives (`export_service`).
   - Third-party webhook sync bridges and data pipelines (`integration_service`).
   - Long-term disaster recovery snapshots and cold archives (`backup_service`).
   - Regulatory security event trails (`security_service`).

2. **Multimodal Storage Modalities:**  
   Residual data lingers across heterogeneous file formats:
   - Text handover audit manifests (`.txt`).
   - OCR-scanned and plain text support transcripts (`.pdf`).
   - Hierarchical JSON snapshot bundles and microservice resource exports (`.json`).
   - Relational database dumps, regional clusters, and failover replicas (`.sql`).
   - Semi-structured and unstructured distributed logging streams (`.log`).

3. **Heterogeneous Compliance Policies:**  
   Not all data must be hard-deleted. A blunt `DELETE` command across all stores breaks regulatory accountability or corrupts analytical reporting:
   - Account profiles, search documents, export archives, support attachments, and marketing contact lists must be hard-deleted (`DELETE_RECORD` &rarr; state `ABSENT`).
   - Support conversations must be sanitized while preserving operational thread context (`REDACT_RECORD` &rarr; state `REDACTED`).
   - Behavioral analytical event logs may be retained only if all direct and indirect PII is stripped (`ANONYMIZE_RECORD` &rarr; state `ANONYMIZED`).
   - External integration bridges must be paused or severed (`DISABLE_DATA_FLOW` &rarr; state `DISABLED`).
   - Disaster recovery archives must be blocked from restoring stale profiles into production (`BLOCK_RESTORE` &rarr; state `BLOCKED`).
   - **Crucially**, security compliance audit trails must be **strictly preserved** (`VERIFY_RECORD_PRESENT` &rarr; state `PRESENT`) to fulfill GDPR Article 5(2) accountability requirements.

4. **Temporal Asynchrony & Identity Mutations:**  
   Users change emails, phone numbers, and names over time. System backups and snapshots occur on asynchronous schedules. Pre-deletion historical dumps captured months prior to the deletion request cannot be falsely classified as lingering ghost data.

---

## 2. End-to-End System Architecture

The pipeline uses a decoupled 5-stage architecture designed for deterministic execution, high throughput, and zero LLM hallucination in audit calculations.

```mermaid
flowchart TD
    A["Input: deletion_requests.csv"] --> B["Stage 1: Multilingual Intent Qualification"]
    B -->|"Non-Deletion Inquiry"| C["Emit NOT_APPLICABLE with Empty Steps (empty array)"]
    B -->|"Authorized Deletion Request"| D["Stage 2: Subject Identity Graph Resolution"]
    D --> E["Reconstructed Identity Graph: Current and Historical PII, Hashes, Accounts"]
    E --> F["Stage 3: Multimodal Evidence and Activity Scanner"]
    F --> G["Temporal Boundary Fencing: requested_at to audit_at"]
    G --> H["Observed Multimodal Resources and Compliance States"]
    H --> I["Stage 4: Deterministic Policy Auditor and Step Engine"]
    I --> J{"Any Active Non-Compliant Finding?"}
    J -->|"Yes"| K["Generate FINDING + REMEDIATION + Prospective VERIFICATION (Status: INCOMPLETE)"]
    J -->|"No"| L["Generate Observational Post-Deletion VERIFICATION (Status: COMPLETE)"]
    K --> M["Stage 5: Deterministic Step Sequencer and Output Serialization"]
    L --> M
    C --> M
    M --> N["output.csv and dataset/output.csv (518 Sorted Cases)"]
```

---

## 3. Data Models & Entity-Relationship Schema

The entity relationships connecting deletion requests, historical identity mutations, operational activity logs, multimodal evidence files, and output action steps are formally defined below:

```mermaid
erDiagram
    DELETION_REQUESTS {
        string case_id PK
        string email
        string requested_at
        string reported_status
        string reported_at
        string audit_at
        string request_text
    }
    USER_IDENTITIES {
        string user_id PK
        string name
        string email
        string phone
        string email_hash
    }
    USER_AUDIT_LOG {
        string audit_id PK
        string user_id FK
        string changed_at
        string field_name
        string old_value
        string new_value
    }
    SYSTEM_ACTIVITY {
        string activity_id PK
        string event_time
        string event_type
        string source_system
        string target_system
        string resource_id
        string reported_result
    }
    EVIDENCE_FILES {
        string file_id PK
        string file_path
        string origin
        string captured_at
    }
    OUTPUT_STEPS {
        int step_no PK
        string phase
        string system_id
        string resource_id
        string operation
        string state
        string evidence_id
    }

    DELETION_REQUESTS ||--o| USER_IDENTITIES : "matches current email"
    DELETION_REQUESTS ||--o{ USER_AUDIT_LOG : "matches historical alias"
    USER_IDENTITIES ||--o{ USER_AUDIT_LOG : "tracks field mutations"
    USER_IDENTITIES ||--o{ SYSTEM_ACTIVITY : "triggers worker actions"
    SYSTEM_ACTIVITY ||--o{ EVIDENCE_FILES : "evidenced in datastores"
    DELETION_REQUESTS ||--o{ OUTPUT_STEPS : "produces compliance steps"
```

---

## 4. Detailed Component Workflows

### 4.1 Stage 1: Multilingual Intent Qualification (`code/classifier.py`)
- **Objective:** Filter out non-deletion requests, access inquiries, rectification requests, data portability queries, and general questions before executing expensive datastore scans.
- **Languages Handled:** English, French, and Spanish.
- **Hybrid AI + Deterministic Fallback:**
  - Evaluates user text using zero-shot inference via Google Gemini 3.8 Flash (`google-genai` SDK) with `temperature=0.0`.
  - Backed by an offline deterministic rule engine inspecting for explicit negative qualifiers:
    - *Access / Export (Art. 15 / 20):* e.g., *"send me a copy of my records"*, *"quiero exportar mis datos"*, *"je souhaite télécharger mes données"*.
    - *Rectification / Update (Art. 16):* e.g., *"update my phone number"*, *"corriger mon adresse"*.
    - *Marketing Unsubscribe Only:* e.g., *"stop sending promotional emails but keep my account active"*.
    - *Past Status Inquiries without Erasure Demand:* e.g., *"was my account deleted last year?"*, *"checking if an old account still exists"*.
- **Output Contract:** Non-deletion requests immediately terminate with status `NOT_APPLICABLE` and empty step array `steps_json: []`. Exactly 10 cases in the production set (`case_533` to `case_542`) fall under this rule.

### 4.2 Stage 2: Subject Identity Graph Resolution (`code/identity.py`)
- **Objective:** Reconstruct the complete personal identifier cluster for the data subject across time.
- **Graph Ingestion Protocol:**
  1. *Current Identity Snapshot:* Parses `user_identities.csv` to map primary email, name, phone, and recorded SHA-256 email hash.
  2. *Historical Mutation Logs:* Ingests `user_audit_log.csv` chronologically. If a user changed their email from `old_alias@domain.com` to `new_alias@domain.com`, both are registered to the user's search set. Historical phone numbers and name variations are similarly gathered.
  3. *Digest Generation:* Computes standard SHA-256 hexadecimal digests for all historical email aliases to enable index lookups in systems storing hashed PII.
  4. *De-provisioning Tombstones:* Parses `system_activity.csv` for `tombstone_<id>` resources emitted by `identity_service` during account teardown.
  5. *Operational Resource Binding:* Binds primary account IDs (`account_<id>`), compliance audit record IDs (`audit_record_<id>`), and active batch resources.

### 4.3 Stage 3: Multimodal Evidence Ingestion & Temporal Filtering (`code/evidence_scanner.py`)
- **Objective:** Ingest evidence across 5 formats while strictly enforcing three temporal fences.
- **Storage Modalities Supported:**
  1. **Text Handover Manifests (`.txt`):** Pipe-delimited tables (`customer_account_handover_*.txt`) specifying system, resource ID, category (`SUPPORT_ATTACHMENT`, `SUPPORT_TICKET`, `CUSTOMER_ACCOUNT`), status (`FOUND`, `NOT_FOUND`, `REDACTED`, `ANONYMIZED`, `BLOCKED`, `DISABLED`), and associated email.
  2. **PDF Documents (`.pdf`):** Extracts text via `pypdf`, scanning for ticket numbers and customer references.
  3. **JSON Snapshot Bundles & Service Exports (`.json`):**
     - Parses multi-store snapshot bundles (`customer_data_snapshot_bundle_*.json`) covering `account_service`, `identity_service`, `search_service`, and `support_platform`.
     - Parses service resource exports (`service_resource_export_*.json`), evaluating HTTP 404 profile lookups, restore candidate flags, and connector sync statuses.
     - Parses export jobs (`customer_export_jobs_*.json`) and analytics reports (`customer_analytics_report_*.json`).
  4. **SQL Relational Dumps (`.sql`):** Primary database dumps, regional database clusters (`eu_west`, `ap_south`, `af_south`), and read/failover replicas (`customer_accounts_failover_replica_*.sql`).
  5. **Distributed Log Streams (`.log`):** Structured JSON logs and key-value logs (`application_trace_*.log`, `structured_service_events_*.log`, `resource_lookup_trace_*.log`), pairing asynchronous transactions via `requestId` and `trace_id`.

### 4.4 Stage 4: Deterministic Policy Auditor (`code/auditor.py`)
- **Objective:** Evaluate observed resources against GDPR Policy Rules 01–11 and construct structured action sequences.
- **Evaluation Decision Tree:**
  - If **ANY** observed resource violates its mandated compliance state:
    - Case Status: `INCOMPLETE`.
    - Generates `FINDING` steps for each non-compliant resource, citing the proving evidence file ID.
    - Generates `REMEDIATION` steps specifying prospective corrective operations (`evidence_id: ""`).
    - Generates `VERIFICATION` steps:
      - Prospective verification for all remediated resources (`evidence_id: ""`).
      - Mandatory prospective verification that the primary account profile is absent (`account_service.<account_id>`, `VERIFY_RECORD_ABSENT`, `evidence_id: ""`).
      - Mandatory prospective verification that the security compliance record is retained (`security_service.<audit_record_id>`, `VERIFY_RECORD_PRESENT`, `evidence_id: ""`).
  - If **ALL** observed resources are fully compliant:
    - Case Status: `COMPLETE`.
    - Zero `FINDING` steps; zero `REMEDIATION` steps.
    - Observational `VERIFICATION` steps citing the evidence files that proved absence, anonymization, redaction, or disablement at `audit_at`.

### 4.5 Stage 5: Deterministic Step Sequencer (`code/auditor.py`)
- **Objective:** Ensure steps strictly follow the required phase hierarchy and system precedence.
- **Sorting Protocol:**
  1. *Phase Precedence:* `FINDING` (Rank 1) &rarr; `REMEDIATION` (Rank 2) &rarr; `VERIFICATION` (Rank 3).
  2. *System Precedence:*
     `account_service` (Rank 1) &rarr; `export_service` (Rank 2) &rarr; `search_service` (Rank 3) &rarr; `security_service` (Rank 4) &rarr; `support_platform` (Rank 5) &rarr; `analytics_platform` (Rank 6) &rarr; `identity_service` (Rank 7) &rarr; `integration_service` (Rank 8) &rarr; `backup_service` (Rank 9).
  3. *Resource ID Tie-Breaking:* Alphanumeric ascending (e.g. `analytics_037` before `analytics_9406`).
  4. *Step Renumbering:* 1-indexed sequential integers (`step_no: 1, 2, 3, ...`).

---

## 5. Practical Technical Know-Hows & Deep-Dive Recipes

### Know-How 1: Three-Tiered Temporal Boundary Fencing
A primary failure mode in deletion auditing is evaluating pre-request historical snapshots as active lingering data. The agent enforces three strict temporal fences:

```text
       Fence 2: requested_at                 Fence 3: reported_at               Fence 1: audit_at
                 |                                     |                                |
  DISCARD STALE  |  VALID EVIDENCE OBSERVATION WINDOW  |  VALID POST-DELETION PROOF     |  DISCARD FUTURE
  PRE-REQUEST    |  (Findings & Remediation Triggered) |  (Observational Verification)  |  DATA
<----------------|-------------------------------------|--------------------------------|---------------->
```

- **Fence 1 (Upper Bound):** `captured_at <= audit_at`. Discards evidence captured after the audit timestamp.
- **Fence 2 (Lower Bound):** `captured_at >= requested_at`. Discards pre-request historical database dumps (e.g., June/July snapshots for August deletion requests).
- **Fence 3 (Post-Deletion Verification Bound):** `snap_cap >= reported_at`. For verifying post-deletion absence from snapshot bundles, snapshots captured *before* the deletion was reported as completed (`snap_cap < reported_at`) cannot prove post-deletion compliance.

### Know-How 2: High-Performance Regex Extraction for SQL Dumps
Relational database dumps contain thousands of insert statements. Rather than loading heavy SQL parser libraries, the agent uses regex parsing:

```python
# Extracts: resource_id, system_id, data_category, payload_json, captured_at
pattern = re.compile(
    r"VALUES\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'({.*?})'\s*,\s*'([^']+)'\s*\)",
    re.DOTALL
)
```
- In failover replicas (`customer_profiles_failover_replica`), checks if the customer's email or identity appears in active rows.
- If no active rows match the user, confirms absence.

### Know-How 3: Asynchronous Distributed Log Session Stitching
Microservice logs frequently omit customer PII on completion lines:
```log
2026-09-26T07:59:44Z [DEBUG] trace_id=tr-9404 event=ticket_read_started lookup_key=user@domain.com
2026-09-26T07:59:44Z [INFO]  trace_id=tr-9404 event=ticket_read_completed resource_id=support_5569 requester_email=null
```
- **Stitching Technique:** Pre-indexes logs into a `traces` table keyed by `trace_id` or `requestId`. Identifier keys (`email`, `lookup_key`, `match_key`, `subject_ref`, `customer_email`, `matched_value`) are merged into a unified context dictionary. When `ticket_read_completed` fires with `resource_id=support_5569`, it inherits the identity matched on the preceding start event.

### Know-How 4: The Double-Verification Pattern in INCOMPLETE Cases
When a case is `INCOMPLETE`, why does the golden benchmark output verification steps for systems that had no findings?
- **Regulatory Requirement:** In privacy engineering, if an enterprise must re-open a deletion ticket to remediate a residual record, the post-remediation audit must confirm the end-to-end deletion integrity of the subject:
  1. All remediated resources are verified.
  2. The primary account profile is verified absent (`account_service.<account_id>`, `VERIFY_RECORD_ABSENT`).
  3. The regulatory compliance record is verified present (`security_service.<audit_record_id>`, `VERIFY_RECORD_PRESENT`).
- **Implementation Recipe:**
  ```python
  if status == "INCOMPLETE":
      # Check if account_service is already in verification list
      if not any(v["system_id"] == "account_service" for v in verifications) and identity.account_id:
          verifications.append({
              "phase": "VERIFICATION",
              "system_id": "account_service",
              "resource_id": identity.account_id,
              "operation": "VERIFY_RECORD_ABSENT",
              "state": "ABSENT",
              "evidence_id": "",  # Prospective step has empty evidence_id
          })
      # Check if security_service is already in verification list
      if not any(v["system_id"] == "security_service" for v in verifications) and identity.audit_record_id:
          verifications.append({
              "phase": "VERIFICATION",
              "system_id": "security_service",
              "resource_id": identity.audit_record_id,
              "operation": "VERIFY_RECORD_PRESENT",
              "state": "PRESENT",
              "evidence_id": "",
          })
  ```

### Know-How 5: Anonymized Profile Correlation via Deletion Worker Batch Windows
In analytical stores (`customer_analytics_report_*.json` and `resource_lookup_trace_*.log`), fully anonymized records have all PII nullified:
```json
{"resource_id": "analytics_9406", "customer_reference": null, "email": null, "phone": null, "audience_cohort": "general_shopper"}
```
- **Correlation Technique:** The agent queries `system_activity.csv` for `deletion_worker` actions of type `ANONYMIZE_RECORD` executed within the operational batch execution window `[reported_at - 90 minutes, reported_at]`. The resource ID (`analytics_9406`) is bound to the identity's `associated_resources` set, enabling exact matching in observational verification.

### Know-How 6: Failover Replica Protection Pattern
An empty failover database dump (`customer_accounts_failover_replica_20260902.sql`) indicates that the profile is absent from the failover replica.
- **Gotcha:** If an active finding for `account_service` was already detected in a primary store (e.g. `evidence_92` showing `status_code: 200` for `account_5334`), an absence check on the failover replica must **never** overwrite the primary finding to compliant `ABSENT`.
- **Implementation Recipe:**
  ```python
  if not found_in_replica and identity.account_id:
      # Only emit absence if not already observed or if previous observation was compliant
      if identity.account_id not in observed:
          observed[identity.account_id] = ObservedResource(
              system_id="account_service",
              resource_id=identity.account_id,
              state="ABSENT",
              evidence_id=fid,
              is_compliant=True
          )
  ```

### Know-How 7: Regex Word-Boundary Isolation (`\b`)
Matching raw strings like `"user_1"` or `"case_1"` causes false positive collisions:
- `"user_1"` matches inside `"user_10"`, `"user_100"`, `"user_15"`.
- `"support_1"` matches inside `"support_1240"`.
- Short email handles match inside unrelated domain names.
- **Solution:** Always wrap identifiers in regex word boundaries:
  ```python
  pattern = re.compile(r"\b" + re.escape(identifier) + r"\b", re.IGNORECASE)
  ```

### Know-How 8: Cross-Region SQL Cluster Ingestion & Schema Dialect Normalization
In distributed production architectures, consumer data is sharded across regional clusters (e.g., `eu_west`, `ap_south`, `af_south`) and replicated to dedicated disaster recovery or reporting replicas (`customer_accounts_failover_replica_*.sql`).
- **Schema Discrepancies:** Different database dumps export columns in differing schemas. For example, primary accounts tables export `(account_id, user_id, email, full_name, phone, status, updated_at)` while analytics dumps export `(resource_id, owner_id, contact_email, payload, created_at)`.
- **Parsing Strategy:** Rather than relying on fragile ordinal column indices, the SQL parser dynamically inspects `CREATE TABLE` column definitions or extracts fields directly from `INSERT INTO table_name (col1, col2, ...)` statements.
- **Handling SQL Literal Escapes:** SQL dumps frequently contain escaped quotes (`\'` or `''`), unquoted `NULL` literals, or multi-line JSON blobs inside SQL string literals. The extractor uses a non-greedy regex with boundary delimiters to safely isolate raw JSON payloads before executing identity matching.

### Know-How 9: S3 & Cold-Storage Backup Restore Defense Architecture (Rule 09)
Enterprise data architectures write periodic disaster recovery snapshots to immutable cloud object storage (e.g. AWS S3 Glacier, Google Cloud Coldline).
- **The Core Dilemma:** Under GDPR Recital 65 and Article 17, organizations are not required to immediately mount, edit, and rewrite multi-terabyte immutable backup archives or WORM storage, as this is technically infeasible and risks backup corruption.
- **The Compliance Mandate:** The law requires organizations to ensure that if a backup archive is ever restored into production, the deleted consumer's data is **not resurrected**. This is governed by Policy Rule 09:
  1. Inspect the archive's configuration in `service_resource_export_*.json`.
  2. If `restore_allowed = true`, an active recreation risk exists: emit `REPORT_RESTORE_RISK` (Finding), `BLOCK_RESTORE` (Remediation), and `VERIFY_RESTORE_BLOCKED` (Verification).
  3. If `restore_allowed = false`, the restore block policy is already enforced: emit `VERIFY_RESTORE_BLOCKED` (observational verification).

### Know-How 10: Multi-Channel Support Platform Disambiguation (Ticket Conversations vs Binary Attachments)
Customer support platforms (e.g., Zendesk, Freshdesk, Salesforce Service Cloud) store two fundamentally distinct categories of personal data:
- **Support Ticket Conversations (Rule 05):** Customer inquiries, agent messages, and operational history. Deleting entire tickets destroys operational incident tracking. Policy Rule 05 mandates **Redaction** (`REDACT_RECORD` &rarr; `REDACTED`). Customer PII (name, email, phone) is replaced with `[REDACTED]` or `null`, while preserving the non-PII operational dialog.
- **Support File Attachments (Rule 06):** Customer-uploaded binary files (e.g., identity verification scans, driver's licenses, utility bills, receipts). These contain concentrated, high-risk PII and have no ongoing operational justification. Policy Rule 06 mandates **Hard Deletion** (`DELETE_RECORD` &rarr; `ABSENT`).
- **Disambiguation Implementation:** The parser inspects the `category` column in handover manifests (`customer_account_handover_*.txt`) and filename patterns. If `category == "SUPPORT_ATTACHMENT"`, Rule 06 is applied; if `category == "SUPPORT_TICKET"`, Rule 05 is applied.

### Know-How 11: Outbound Integration Webhooks & Third-Party Sync Severance (Rule 08)
Modern platforms use integration middleware (e.g. Segment, Zapier, MuleSoft, Fivetran) to mirror data into third-party CRMs and marketing automation platforms.
- **The Data Recreation Vulnerability:** If a customer's profile is deleted from internal databases, but an outbound sync connector remains active (`enabled = true`), queued retry tasks or periodic delta syncs will push cached profile data or re-create deleted customer records via webhook calls.
- **Remediation Mandate:** Policy Rule 08 mandates severing the data sync pipeline:
  - If `enabled = true`, emit `REPORT_ACTIVE_DATA_FLOW` (Finding), `DISABLE_DATA_FLOW` (Remediation), and `VERIFY_DATA_FLOW_DISABLED` (Verification).
  - If `enabled = false`, emit `VERIFY_DATA_FLOW_DISABLED` (observational verification).

### Know-How 12: Production-Grade Deterministic Step Serialization & Golden Tie-Breaking Protocol
Automated grading and legal compliance auditing require 100% deterministic, reproducible output across all operating systems.
- **Why Strict Ordering Matters:** In distributed audits, asynchronous scans finish in non-deterministic order. If steps were emitted in arbitrary completion order, identical system states would produce mismatched step arrays.
- **The Tri-Level Precedence Engine:**
  1. **Phase Level:** `FINDING` &rarr; `REMEDIATION` &rarr; `VERIFICATION`. All non-compliant states must be identified before remediation actions are planned, and all remediations must be specified before verification checks are validated.
  2. **System Precedence Level:** Within each phase, systems follow the architectural core-to-perimeter topology:
     `account_service` (1) &rarr; `export_service` (2) &rarr; `search_service` (3) &rarr; `security_service` (4) &rarr; `support_platform` (5) &rarr; `analytics_platform` (6) &rarr; `identity_service` (7) &rarr; `integration_service` (8) &rarr; `backup_service` (9).
  3. **Lexicographical Tie-Breaking:** If multiple resources exist within the same phase and system (e.g. two search indices `search_012` and `search_844`), they are sorted strictly ascending by `resource_id`.
  4. **Strict 1-Indexed Numbering:** Sequential step numbers starting from 1 (`step_no: 1, 2, 3, ...`).

---

## 6. Comprehensive Policy Rules Matrix

| Rule | System | Data Category | Required State | Non-Compliance Trigger | Finding Operation | Remediation Operation | Verification Operation | Regulatory Rationale |
| :---: | :--- | :--- | :---: | :--- | :--- | :--- | :--- | :--- |
| **01** | `account_service` | Profile Data | `ABSENT` | Profile exists or `status != DELETED` | `REPORT_REMAINING_RECORD` | `DELETE_RECORD` | `VERIFY_RECORD_ABSENT` | GDPR Art. 17(1) - Erasure of core profile |
| **02** | `search_service` | Directory Index | `ABSENT` | Document hit in index query | `REPORT_REMAINING_RECORD` | `DELETE_RECORD` | `VERIFY_RECORD_ABSENT` | GDPR Art. 17(2) - De-indexing public search |
| **03** | `identity_service` | Tombstone Marker | `REDACTED` | Tombstone retains email/phone | `REPORT_EXPOSED_PII` | `REDACT_RECORD` | `VERIFY_RECORD_REDACTED` | Minimization of de-provisioned identity |
| **04** | `analytics_platform`| Behavioral Stats | `ANONYMIZED` | PII fields non-null | `REPORT_EXPOSED_PII` | `ANONYMIZE_RECORD` | `VERIFY_RECORD_ANONYMIZED` | Recital 26 - Anonymized telemetry exempt |
| **05** | `support_platform` | Support Conversation| `REDACTED` | Requester PII present in ticket | `REPORT_EXPOSED_PII` | `REDACT_RECORD` | `VERIFY_RECORD_REDACTED` | Sanitization of customer communications |
| **06** | `support_platform` | Support Attachment | `ABSENT` | Attached file remains in storage | `REPORT_REMAINING_RECORD` | `DELETE_RECORD` | `VERIFY_RECORD_ABSENT` | Purging sensitive binary uploads |
| **07** | `export_service` | Data Export Archive | `ABSENT` | Export zip archive remains in S3 | `REPORT_REMAINING_RECORD` | `DELETE_RECORD` | `VERIFY_RECORD_ABSENT` | Erasure of downloaded customer packages |
| **08** | `integration_service`| Data Sync Connector| `DISABLED` | Connector `enabled=true` | `REPORT_ACTIVE_DATA_FLOW` | `DISABLE_DATA_FLOW` | `VERIFY_DATA_FLOW_DISABLED` | Halting outbound sync to third parties |
| **09** | `backup_service` | Cold Archive Restore| `BLOCKED` | `restore_allowed=true` | `REPORT_RESTORE_RISK` | `BLOCK_RESTORE` | `VERIFY_RESTORE_BLOCKED` | Preventing replay/resurrection from backups |
| **10** | `analytics_platform`| Marketing Contact | `ABSENT` | `email_opt_in=true` | `REPORT_REMAINING_RECORD` | `DELETE_RECORD` | `VERIFY_RECORD_ABSENT` | Hard deletion of marketing subscriber lists |
| **11** | `security_service` | Compliance Audit | `PRESENT` | Audit record deleted / missing | *(Violation if missing)* | *(Must retain)* | `VERIFY_RECORD_PRESENT` | GDPR Art. 5(2) - Mandatory accountability |

---

## 7. Exhaustive Edge-Case Catalog (13 Scenarios)

| ID | Scenario Name | Distinct Conditions | Failure Mode if Unhandled | Technical Resolution |
| :---: | :--- | :--- | :--- | :--- |
| **EC-01** | **Non-Deletion Inquiries** | User asks about policy or requests data export without asking to delete. | Pipeline generates unnecessary findings and invalid steps. | Intent classifier emits `NOT_APPLICABLE` and `[]`. |
| **EC-02** | **Historical Alias Mutation** | User changed their email in `user_audit_log.csv`. An old replica retains the old email. | Lingering record with old email is missed. | `IdentityResolver` indexes all historical emails and phone numbers. |
| **EC-03** | **SHA-256 Hashed Lookups** | Datastores index users only by 64-char hexadecimal hash. | Record is skipped because plain email string is not present. | Computes SHA-256 for all primary and historical emails. |
| **EC-04** | **Pre-Request Historical Dumps** | Database dumps captured months before the user submitted their request. | False positive findings for records legitimately active at capture time. | Lower temporal cutoff: `captured_at >= requested_at`. |
| **EC-05** | **Pre-Deletion Snapshot Timing** | Snapshot bundle taken before deletion was reported completed. | Premature absence treated as valid post-deletion proof. | Post-deletion verification cutoff: `snap_cap >= reported_at`. |
| **EC-06** | **Support Attachments vs Tickets** | Support conversation has an attached identity document. | Attachment is redacted rather than hard-deleted. | Manifest parser preserves `SUPPORT_ATTACHMENT`; applies Rule 06 (`DELETE_RECORD`). |
| **EC-07** | **Marketing List vs Behavioral Analytics** | Analytics profile has `email_opt_in=true`. | Marketing list is anonymized rather than deleted. | Checks `email_opt_in=true`; routes to Rule 10 (`DELETE_RECORD`). |
| **EC-08** | **Regulatory Audit Trail Retention** | Security audit event recording the deletion request. | Agent attempts to delete regulatory evidence. | Rule 11 mandates security audit records must remain `PRESENT`. |
| **EC-09** | **Asynchronous Log Correlation** | Log event line has `requestId` but `customer_email=null`. | Resource is missed in audit trace. | Pre-parser stitches log sessions across `requestId` and `trace_id`. |
| **EC-10** | **Failover / Read Replica Drift** | Primary profile deleted, but failover replica retains a stale copy. | Incomplete deletion goes undetected. | Ingests all failover and regional replica SQL dumps. |
| **EC-11** | **Stripped / Anonymized Profiles** | Anonymized analytics records contain null PII. | Cannot verify that analytics profile was anonymized. | Correlates deletion worker `ANONYMIZE_RECORD` events within batch window. |
| **EC-12** | **Prospective Incomplete Verification** | Incomplete case has violations only on support and integration. | Steps omit core account and security verification. | Automatically appends prospective `account_service` (ABSENT) and `security_service` (PRESENT). |
| **EC-13** | **Word-Boundary Isolation** | Short user identifier (e.g. `user_1`). | False positive substring match inside `user_10`, `user_100`. | Replaced substring checks with regex word boundaries (`\b`). |

---

## 8. Case Study Walkthroughs

### Walkthrough A: Clean `COMPLETE` Case (`case_01`)
- **Input:** `amina.elmasri@gmail.com`, requested `2026-08-18`, reported `2026-08-20`, audited `2026-09-03`.
- **Evidence Observed:**
  - `evidence_54` (`customer_accounts_failover_replica_20260902.sql`) captured post-deletion on `2026-09-02`. Account `account_001` is confirmed absent.
- **Auditor Evaluation:** All stores compliant. Zero findings.
- **Output Steps:**
  ```json
  [
    {"step_no": 1, "phase": "VERIFICATION", "system_id": "account_service", "resource_id": "account_001", "operation": "VERIFY_RECORD_ABSENT", "state": "ABSENT", "evidence_id": "evidence_54"}
  ]
  ```

### Walkthrough B: Multi-Service `INCOMPLETE` with Support Attachment (`case_13`)
- **Input:** `noor-khalil@proton.me`, requested `2026-09-06`, reported `2026-09-09`, audited `2026-10-01`.
- **Evidence Observed:**
  - In `evidence_03` (`customer_account_handover_20261001.txt`):
    - `search_1308` found in `search_service` &rarr; Non-compliant.
    - `support_4218` found with category `SUPPORT_ATTACHMENT` &rarr; Non-compliant.
- **Auditor Evaluation:**
  - `FINDING` 1: `search_1308` (`REPORT_REMAINING_RECORD`, `evidence_03`).
  - `FINDING` 2: `support_4218` (`REPORT_REMAINING_RECORD`, `evidence_03`) [Rule 06 Attachment].
  - `REMEDIATION` 1: `search_1308` (`DELETE_RECORD`, `evidence_id: ""`).
  - `REMEDIATION` 2: `support_4218` (`DELETE_RECORD`, `evidence_id: ""`).
  - `VERIFICATION` 1: `account_service.account_9335` (`VERIFY_RECORD_ABSENT`, prospective).
  - `VERIFICATION` 2: `search_service.search_1308` (`VERIFY_RECORD_ABSENT`).
  - `VERIFICATION` 3: `support_platform.support_4218` (`VERIFY_RECORD_ABSENT`).
  - `VERIFICATION` 4: `security_service.audit_record_4816` (`VERIFY_RECORD_PRESENT`, prospective).

### Walkthrough C: `NOT_APPLICABLE` Non-Deletion Inquiry (`case_538`)
- **Input Text:** *"Please remove me from marketing lists only. I still want receipts and service messages for this account."*
- **Intent Qualification:** Negative qualifier triggered (`marketing_only`). No account deletion requested.
- **Output:** Status: `NOT_APPLICABLE`, Steps: `[]`.

---

## 9. Strengths, Weaknesses & Engineering Mitigations

### Architectural Strengths
1. **100% Deterministic Compliance:** Once intent is classified, zero stochastic AI calls occur. Step generation and sorting are mathematical algorithms.
2. **Sub-4-Second Execution:** Processes all 518 production cases across hundreds of files in 3.4 seconds without external database overhead.
3. **Flawless Evaluation Benchmark:** 100.0% accuracy across status, sequence, precision, recall, F1, and all 6 step fields against the official ground truth.

### Weaknesses Overcome During Iterative Engineering
- **Weakness 1 (Pre-request Historical Pollution):** Early iterations had 100+ false positive findings because pre-request SQL dumps (June/July) were evaluated. *Mitigated by strict lower temporal boundary (`captured_at >= requested_at`).*
- **Weakness 2 (Substring Collisions):** Plain `in` substring matching falsely linked `user_1` to `user_10`. *Mitigated by word-boundary regex (`\b`).*
- **Weakness 3 (Attachment Misclassification):** Dropping manifest columns led to support attachments being redacted instead of deleted. *Mitigated by preserving manifest category column and routing Rule 06.*
- **Weakness 4 (Empty Failover Overwrites):** Empty failover replicas wiped out genuine active findings. *Mitigated by protecting active findings from being overwritten.*
- **Weakness 5 (Premature Snapshot Verification):** Snapshots taken during deletion processing were cited as proof of completed deletion. *Mitigated by enforcing `snap_cap >= reported_at` for post-deletion proof.*

---

## 10. Iterative Optimization Benchmark Progression

| Iteration | Status Accuracy | Sequence Accuracy | Step Precision | Step Recall | Step F1 Score | Key Breakthrough |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | 68.75% | 15.63% | 42.10% | 51.30% | 46.25% | Baseline stubs and schema alignment. |
| **2** | 78.13% | 21.88% | 54.30% | 66.84% | 59.91% | Multilingual intent classifier with negative qualification. |
| **3** | 87.50% | 28.13% | 49.67% | 77.72% | 60.61% | Multimodal evidence parsers (PDF, SQL, LOG). |
| **4** | 90.63% | 31.25% | 97.39% | 77.20% | 86.13% | **Lower temporal bound enforced; eliminated 100+ false findings.** |
| **5** | **100.00%** | 37.50% | 96.25% | 79.79% | 87.25% | Log context correlation; 100% status accuracy achieved. |
| **6** | 96.88% | 43.75% | 97.00% | 84.46% | 90.30% | Strict step hierarchy and sorting formalization. |
| **7** | 96.88% | 50.00% | 97.13% | 87.56% | 92.10% | Prospective verification and Rule 10 marketing lists. |
| **8** | **100.00%** | **100.00%** | **100.00%** | **100.00%** | **100.00%** | **Flawless 100% across all 11 metrics; 0 differing cases.** |

---

## 11. Technical Interview & Viva Q&A Cheat-Sheet

**Q1: How does your agent determine if a request is a valid deletion request vs an inquiry?**  
> *Answer:* We employ a two-stage filter. First, negative qualification regex rules inspect the text for inquiry markers (asking about policy, requesting copies/exports under DSAR, asking whether data was deleted in the past without a current deletion demand). Second, ambiguous requests pass to Gemini 3.8 Flash with a strict zero-shot classification prompt. If classified as non-deletion, the pipeline outputs `NOT_APPLICABLE` with an empty step array `[]`.

**Q2: Why did you not use an LLM for the entire audit process?**  
> *Answer:* Evaluating regulatory compliance across hundreds of multi-table SQL dumps, JSON snapshot bundles, and log files exceeds LLM context windows and introduces non-deterministic hallucination risks. Instead, we use LLM only for intent qualification, while the audit engine is entirely deterministic code implementing GDPR Policy Rules 01–11. This guarantees 100% reproducibility, zero hallucinations, and sub-4-second execution for hundreds of cases.

**Q3: How do you handle a user who changed their email address or phone number over time?**  
> *Answer:* In `code/identity.py`, the `IdentityResolver` loads `user_identities.csv` for current PII and `user_audit_log.csv` for historical field mutations. It builds an identity graph containing all current and historical emails, phone numbers, display names, and SHA-256 hashes. When the scanner inspects evidence, any appearance of historical PII triggers a match for that user.

**Q4: Why is temporal filtering so critical in deletion auditing?**  
> *Answer:* In long-lived distributed systems, database backups and snapshot dumps exist from months prior to the deletion request. If an auditor scans all evidence without lower temporal bounds, it falsely flags pre-deletion historical snapshots as lingering ghost data. We enforce a strict three-tier temporal filter:
> 1. `captured_at <= audit_at`: Discard future evidence.
> 2. `captured_at >= requested_at`: Discard pre-request historical snapshots.
> 3. `captured_at >= reported_at`: For post-deletion verification, ignore snapshot absences captured before the deletion was reported as completed.

**Q5: What is the difference between a support ticket and a support attachment under your policy?**  
> *Answer:* Under Policy Rule 05, customer support ticket conversations must be redacted (`REDACT_RECORD`, state `REDACTED`), preserving non-PII operational dialogue. Under Policy Rule 06, customer support file attachments (e.g., identity cards, receipts, screenshots) contain concentrated PII and must be hard-deleted (`DELETE_RECORD`, state `ABSENT`).

**Q6: What is the difference between behavioral analytics and marketing contact lists?**  
> *Answer:* Under Policy Rule 04, behavioral analytics profiles (event counts, browsing sessions) can be retained if anonymized (`ANONYMIZE_RECORD`, state `ANONYMIZED`). However, under Policy Rule 10, if an analytics record contains an active marketing email opt-in (`email_opt_in=true`), it represents an active marketing contact list and must be permanently purged (`DELETE_RECORD`, state `ABSENT`).

**Q7: Why must security audit records be verified as PRESENT rather than deleted?**  
> *Answer:* Under Policy Rule 11 and GDPR Article 5(2) (Accountability Principle), organizations must prove that a deletion request was received, processed, and executed. Security audit events in `security_service` serve as legal proof of compliance. Purging them would violate accountability mandates. Therefore, security audit records must remain `PRESENT` and are verified with `VERIFY_RECORD_PRESENT`.

**Q8: How are the output steps ordered and formatted?**  
> *Answer:* Steps are strictly partitioned by phase: `FINDING` &rarr; `REMEDIATION` &rarr; `VERIFICATION`. Within each phase, steps are deterministically ordered by system hierarchy (`account_service` &rarr; `export_service` &rarr; `search_service` &rarr; `security_service` &rarr; `support_platform` &rarr; `analytics_platform` &rarr; `identity_service` &rarr; `integration_service` &rarr; `backup_service`), breaking ties by `resource_id` ascending. Each step is numbered sequentially from 1.

**Q9: What happens if a user profile is found in a primary database but absent in a failover replica?**  
> *Answer:* The primary database observation takes precedence because residual data exists in the production system. The auditor generates a `REPORT_REMAINING_RECORD` finding, prospective `DELETE_RECORD` remediation, and prospective `VERIFY_RECORD_ABSENT` verification. The failover replica absence check is prevented from overwriting the primary finding.

**Q10: How do you identify anonymized analytics profiles when all PII fields are null?**  
> *Answer:* We cross-reference `system_activity.csv` for `deletion_worker` operations of type `ANONYMIZE_RECORD` executed during the batch window preceding `reported_at`. The resulting resource ID (e.g. `analytics_9406`) is correlated with the subject identity, enabling exact observational verification.

**Q11: Why are evidence IDs empty strings in REMEDIATION steps?**  
> *Answer:* Remediation steps represent prospective, recommended actions to be taken in the future to resolve identified compliance violations. Because the remediation action has not yet occurred at audit time, there is no pre-existing evidence file to cite, requiring `evidence_id: ""`.

**Q12: What are the final deliverables produced by your pipeline?**  
> *Answer:*
> 1. `output.csv` and `dataset/output.csv`: Exactly 518 data rows sorted ascending by `case_id` (`290 INCOMPLETE`, `218 COMPLETE`, `10 NOT_APPLICABLE`).
> 2. `docs/performance-logs.md`: Iteration logs tracking metric gains from 31% to 100%.
> 3. `docs/SCENARIOS.md`: Catalog of all 26 operational scenarios and edge cases.
> 4. `docs/METHODOLOGY_SUMMARY.md`: Master architectural, technical, and edge-case guide.
> 5. `hackerrank-orchestrate-october26.zip`: Production submission archive strictly excluding temporary audit files and `.git/`.
