# Deletion-Audit Scenario & Edge Case Matrix

This document provides a comprehensive catalog of all operational scenarios, edge cases, identity permutations, evidence states, and expected outputs for the **Ghost Data Still Exists** challenge.

---

## Scenario Overview Matrix

| Category | ID | Scenario Name | Input / Evidence Signature | Verdict | Expected Output Pattern |
|---|---|---|---|---|---|
| **1. Intent (Filter 1)** | `SC-01` | Marketing Opt-Out Only | "Please remove me from marketing lists only..." | `NOT_APPLICABLE` | `case_id,NOT_APPLICABLE,[]` |
| | `SC-02` | Data Access Request (GDPR Art. 15) | "I want a copy of all data stored about me." | `NOT_APPLICABLE` | `case_id,NOT_APPLICABLE,[]` |
| | `SC-03` | Data Portability / Export (GDPR Art. 20) | "Please export my transaction history to CSV." | `NOT_APPLICABLE` | `case_id,NOT_APPLICABLE,[]` |
| | `SC-04` | Profile Rectification (GDPR Art. 16) | "My address and phone number changed, please update." | `NOT_APPLICABLE` | `case_id,NOT_APPLICABLE,[]` |
| | `SC-05` | Multilingual Deletion Request | Deletion requested in Spanish/French/Japanese/Korean/German | Process Case | Evaluated against systems |
| **2. Identity Resolution** | `SC-06` | Current Primary Email Match | Request email matches `user_identities.email` directly | Process Case | Map to `user_id` |
| | `SC-07` | Historical Email Alias Shift | Request email is obsolete, found only in `user_audit_log.csv` | Process Case | Trace `old_value` to `user_id` |
| | `SC-08` | Multiple Identity Modifications | User changed email, phone, and name over time | Process Case | Cross-match all alias variants |
| | `SC-09` | Decoy Identity Collision | Similar email/name belongs to another user (e.g. `case_28`) | Disambiguate | Do not match decoy records |
| | `SC-10` | Email Casing & Normalization | Uppercase in request, lowercase in datastores | Normalize | Standardize via lowercase |
| **3. Workflow Claim vs Truth** | `SC-11` | False Positive (`COMPLETE` Claim) | Workflow claims `COMPLETE`, but replica or logs retain PII | `INCOMPLETE` | Findings + Remediation + Verification |
| | `SC-12` | False Negative (`NOT_STARTED` / `PARTIAL`) | Workflow claims incomplete, but systems are fully clean | `COMPLETE` | Verification steps only |
| | `SC-13` | True Negative (`NOT_STARTED` / `PARTIAL`) | Workflow claims incomplete, and records still exist | `INCOMPLETE` | Findings + Remediation + Verification |
| | `SC-14` | True Positive (`COMPLETE` Claim) | Workflow claims `COMPLETE`, and evidence proves state | `COMPLETE` | Verification steps only |
| **4. Temporal Boundaries** | `SC-15` | Evidence Captured Before Cutoff | Snapshot captured `<= audit_at` | Valid Evidence | Eligible for citation in step |
| | `SC-16` | Evidence Captured After Cutoff | Snapshot captured `> audit_at` | Invalid Evidence | Must be discarded |
| **5. Policy Violations & State** | `SC-17` | Account Tombstone Exposed PII | Tombstone retains name/email/phone (`rule_15`) | `INCOMPLETE` | `REPORT_EXPOSED_PII` &rarr; `REDACT_RECORD` |
| | `SC-18` | Compliant Account Tombstone | Tombstone retains only `user_id`, PII is null | `COMPLETE` | `VERIFY_RECORD_REDACTED` |
| | `SC-19` | Retained Security Audit Log | Security log within retention period (`rule_12`) | Compliant | `VERIFY_RECORD_PRESENT` |
| | `SC-20` | Active Data Flow Recreating Data | Connector sync enabled (`enabled = true`) | `INCOMPLETE` | `REPORT_ACTIVE_DATA_FLOW` &rarr; `DISABLE_DATA_FLOW` |
| | `SC-21` | Inactive / Disabled Data Flow | Connector sync stopped (`enabled = false`) | Compliant | `VERIFY_DATA_FLOW_DISABLED` |
| | `SC-22` | Active Backup Restore Risk | Backup archive has `restore_allowed = true` (`rule_14`) | `INCOMPLETE` | `REPORT_RESTORE_RISK` &rarr; `BLOCK_RESTORE` |
| | `SC-23` | Blocked Backup Restore Path | Backup archive has `restore_allowed = false` | Compliant | `VERIFY_RESTORE_BLOCKED` |
| | `SC-24` | Exposed Support Conversation PII | Support ticket contains user email/name (`rule_05`) | `INCOMPLETE` | `REPORT_EXPOSED_PII` &rarr; `REDACT_RECORD` |
| | `SC-25` | Redacted Support Conversation | Support ticket PII is null, context retained | Compliant | `VERIFY_RECORD_REDACTED` |
| | `SC-26` | Exposed Analytics Profile | Analytics profile contains email/phone (`rule_07`) | `INCOMPLETE` | `REPORT_EXPOSED_PII` &rarr; `ANONYMIZE_RECORD` |
| | `SC-27` | Anonymized Analytics Profile | Analytics profile contains only cohort data | Compliant | `VERIFY_RECORD_ANONYMIZED` |
| | `SC-28` | Search Index Directory Ghost | Profile appears in search query hits (`rule_03`) | `INCOMPLETE` | `REPORT_REMAINING_RECORD` &rarr; `DELETE_RECORD` |
| | `SC-29` | Residual Export Archive | Customer `.zip` download still in storage (`rule_09`) | `INCOMPLETE` | `REPORT_REMAINING_RECORD` &rarr; `DELETE_RECORD` |
| | `SC-30` | Replica Replication Drift | Record deleted from primary, but exists in failover | `INCOMPLETE` | `REPORT_REMAINING_RECORD` &rarr; `DELETE_RECORD` |

---

## 1. Intent Classification Scenarios (Filter 1)

Section 6.5 of `AGENTS.md` mandates that before performing any audit, the agent must verify whether `request_text` authorizes account/profile deletion.

### Scenario `SC-01`: Marketing Opt-Out Only
* **Description:** The user wants to stop receiving marketing emails, promotional alerts, or newsletter campaigns, but explicitly keeps their account open for orders and receipts.
* **Input Example (`dataset/deletion_requests.csv:507`):**
  ```csv
  case_538,morgan.amelia@icloud.com,2026-08-31T12:00:00Z,NOT_STARTED,2026-09-03T12:00:00Z,2026-09-26T12:00:00Z,"Please remove me from marketing lists only. I still want receipts and service messages for this account."
  ```
* **Evaluation:**
  - Intent is `MARKETING_OPT_OUT`.
  - Account deletion is **not authorized**.
* **Expected Output:**
  ```csv
  case_538,NOT_APPLICABLE,[]
  ```

---

### Scenario `SC-02`: Data Subject Access Request (GDPR Art. 15 / CCPA)
* **Description:** The user requests to know what data the company holds about them or requests a summary of their account records without requesting account closure or data erasure.
* **Input Example:**
  ```csv
  case_801,nathan.ross@gmail.com,2026-08-15T10:00:00Z,NOT_STARTED,2026-08-16T10:00:00Z,2026-09-01T10:00:00Z,"Under GDPR Article 15, please send me a full copy and breakdown of all personal data your services maintain regarding my profile."
  ```
* **Evaluation:**
  - Intent is `DATA_ACCESS`.
  - Erasure is **not authorized**.
* **Expected Output:**
  ```csv
  case_801,NOT_APPLICABLE,[]
  ```

---

### Scenario `SC-03`: Data Portability / Export Request (GDPR Art. 20)
* **Description:** The user requests a downloadable data export of their historical transactions or profile information without requesting account closure.
* **Input Example:**
  ```csv
  case_802,julie.v@yahoo.fr,2026-08-20T08:00:00Z,COMPLETE,2026-08-21T08:00:00Z,2026-09-05T08:00:00Z,"Pouvez-vous m'envoyer un lien pour télécharger toutes mes factures et historiques de commande au format CSV ?"
  ```
* **Evaluation:**
  - Intent is `DATA_EXPORT`.
  - Erasure is **not authorized**.
* **Expected Output:**
  ```csv
  case_802,NOT_APPLICABLE,[]
  ```

---

### Scenario `SC-04`: Profile Rectification (GDPR Art. 16)
* **Description:** The user informs customer support that their contact information (phone, address, surname) has changed and requests an update.
* **Input Example:**
  ```csv
  case_803,h.tanaka@docomo.ne.jp,2026-08-10T09:00:00Z,NOT_STARTED,2026-08-11T09:00:00Z,2026-09-01T09:00:00Z,"電話番号と配送先住所が変更になりましたので、登録情報の更新をお願いいたします。"
  ```
* **Evaluation:**
  - Intent is `RECTIFICATION`.
  - Erasure is **not authorized**.
* **Expected Output:**
  ```csv
  case_803,NOT_APPLICABLE,[]
  ```

---

### Scenario `SC-05`: Multilingual Deletion Authorization
* **Description:** The user authorizes full account deletion in a non-English language.
* **Input Examples in Dataset:**
  - **Spanish (`case_02`):**
    > *"Intenté eliminar mi cuenta ayer, pero la página terminó mostrando un error. ¿Pueden comprobar si todavía queda algún dato y completar la eliminación si hace falta?"*
  - **French (`case_03`):**
    > *"Je demande la suppression définitive du compte associé à cette adresse e-mail. Veuillez examiner les identifiants actuels et antérieurs conformément à votre procédure de confidentialité."*
  - **Japanese (`case_14`):**
    > *"このメールアドレスに関連するアカウントの完全な削除を依頼します。プライバシー手続きに従い、現在および過去の識別情報を確認してください。"*
  - **Korean (`case_66`):**
    > *"이 이메일 주소에 연결된 계정의 영구 삭제를 요청합니다. 개인정보 처리 절차에 따라 현재 및 이전 식별자를 검토해 주세요."*
  - **Portuguese (`case_54`):**
    > *"Solicito a exclusão permanente da conta associada a este e-mail. Verifiquem os identificadores atuais e anteriores conforme o processo de privacidade."*
* **Evaluation:**
  - Intent is `DELETION`.
  - Proceeds to Stage 2 (Identity Resolution) and Stage 3 (Evidence Audit).

---

## 2. Identity Resolution & Alias Permutations

### Scenario `SC-06`: Direct Primary Email Lookup
* **Signature:** The email in `deletion_requests.csv` matches `user_identities.csv:email` directly.
* **Example (`case_01`):**
  - Request email: `amina.elmasri@gmail.com`
  - In `user_identities.csv`:
    `user_01,Amina El-Masri,amina.elmasri@gmail.com,+971 50 482 7316,d4e1f59abcf9a1e0...`
* **Resolution Result:**
  - `user_id = "user_01"`
  - `name = "Amina El-Masri"`
  - `phone = "+971 50 482 7316"`
  - `email_hash = "d4e1f59abcf9a1e0cfdc7c27ad6c07ed4ff88b326a16ed5eed5ec6bc31618c93"`

---

### Scenario `SC-07`: Historical Email Alias Shift
* **Signature:** The request email is NOT in `user_identities.csv`, but exists in `user_audit_log.csv` as an older address.
* **Example (`case_10`):**
  - Request email: `nadia.ionescu@yahoo.com`
  - In `user_identities.csv`: `user_10` has email `n.petrescu@yahoo.com`.
  - In `user_audit_log.csv:122`:
    `audit_121,user_10,2025-12-13T08:17:43Z,email,nadia.ionescu@yahoo.com,nadia.petrescu@yahoo.com`
* **Resolution Result:**
  - Resolved `user_id = "user_10"`
  - Monitored emails: `{"nadia.ionescu@yahoo.com", "nadia.petrescu@yahoo.com", "n.petrescu@yahoo.com"}`
  - Both old and new email addresses are tracked across system activity and evidence logs (e.g. `support_replica.log`).

---

### Scenario `SC-08`: Decoy Identity Disambiguation
* **Signature:** User text explicitly mentions a decoy or a similar name exists in the database.
* **Example (`case_28`):**
  - User notes: *"Can you verify that my account was deleted? A search result with a similar email belongs to someone else, so please do not treat that record as mine."*
  - In `evidence_54` / read replicas, multiple users share partial name strings (e.g. `Mateo Rios Gil` vs `Mateo Ríos`).
* **Resolution Result:**
  - The agent matches strictly against verified `user_id` and exact alias hashes, ignoring records attributable to other distinct `user_id`s.

---

### Scenario `SC-09`: Email Casing Normalization
* **Signature:** Request email has uppercase characters (e.g., `case_38`: `SIPHO.MOKOENA@GMAIL.COM` or `case_40`: `CHOI.JIHOON94@GMAIL.COM`).
* **Resolution Result:**
  - Normalization to lowercase (`sipho.mokoena@gmail.com`) guarantees matching against database snapshots and SHA-256 hash generation.

---

## 3. Workflow Claim vs Ground Truth Discrepancies

### Scenario `SC-10`: The "Ghost Data" False Positive (`COMPLETE` Claim &rarr; `INCOMPLETE` Reality)
* **Signature:** `reported_status = COMPLETE`, but evidence captured on or before `audit_at` shows records remaining in replicas or secondary systems.
* **Example (`case_05` - Leila Haddad):**
  - Request: `case_05,leila.haddad@yahoo.com,2026-08-27T14:17:00Z,COMPLETE,2026-08-28T09:03:00Z,2026-09-08T13:40:00Z`
  - Deletion claimed complete on `2026-08-28`.
  - In `evidence_54` (`customer_accounts_failover_replica_20260902.sql`) captured at `2026-09-02`:
    ```sql
    INSERT INTO "customer_profiles_failover_replica" VALUES('account_005','user_05','Leila Haddad','leila.haddad@yahoo.com','+212 6 48 27 15 93','ACTIVE','2026-09-02T22:45:00Z');
    ```
    `account_005` is absent from primary, but **present in failover replica**!
* **Expected Output:**
  ```csv
  case_05,INCOMPLETE,"[{""evidence_id"":""evidence_54"",""operation"":""REPORT_REMAINING_RECORD"",""phase"":""FINDING"",""resource_id"":""account_005"",""state"":""PRESENT"",""step_no"":1,""system_id"":""account_service""},{""evidence_id"":"""",""operation"":""DELETE_RECORD"",""phase"":""REMEDIATION"",""resource_id"":""account_005"",""state"":""ABSENT"",""step_no"":2,""system_id"":""account_service""},{""evidence_id"":"""",""operation"":""VERIFY_RECORD_ABSENT"",""phase"":""VERIFICATION"",""resource_id"":""account_005"",""state"":""ABSENT"",""step_no"":3,""system_id"":""account_service""}]"
  ```

---

### Scenario `SC-11`: False Negative (`PARTIALLY_COMPLETE` / `NOT_STARTED` Claim &rarr; `COMPLETE` Reality)
* **Signature:** Workflow reported `PARTIALLY_COMPLETE` or `NOT_STARTED`, but evidence proves that all required purges, anonymizations, and blocks were achieved by `audit_at`.
* **Example (`case_02` - Mateo Rios):**
  - Request: `case_02,mateo.rios@outlook.com,2026-08-21T18:06:00Z,PARTIALLY_COMPLETE,2026-08-22T07:25:00Z,2026-09-04T15:00:00Z`
  - In `system_activity.csv`, deletion worker reported `PARTIAL`.
  - In `evidence_54` (`2026-09-02T23:00:00Z <= audit_at`), `account_002` is completely absent from both primary and replica tables.
* **Expected Output:**
  ```csv
  case_02,COMPLETE,"[{""evidence_id"":""evidence_54"",""operation"":""VERIFY_RECORD_ABSENT"",""phase"":""VERIFICATION"",""resource_id"":""account_002"",""state"":""ABSENT"",""step_no"":1,""system_id"":""account_service""}]"
  ```

---

### Scenario `SC-12`: True Positive (`COMPLETE` Claim &rarr; `COMPLETE` Reality)
* **Signature:** Deletion was claimed complete, and multimodal evidence verifies that every copy received compliant treatment.
* **Example (`case_04` - Thandiwe Ndlovu):**
  - Account service profile is verified absent via `evidence_54`.
  - Analytics profile `analytics_901` is verified anonymized via `evidence_56`.
* **Expected Output:**
  ```csv
  case_04,COMPLETE,"[{""evidence_id"":""evidence_54"",""operation"":""VERIFY_RECORD_ABSENT"",""phase"":""VERIFICATION"",""resource_id"":""account_004"",""state"":""ABSENT"",""step_no"":1,""system_id"":""account_service""},{""evidence_id"":""evidence_56"",""operation"":""VERIFY_RECORD_ANONYMIZED"",""phase"":""VERIFICATION"",""resource_id"":""analytics_901"",""state"":""ANONYMIZED"",""step_no"":2,""system_id"":""analytics_platform""}]"
  ```

---

## 4. Policy Rules & Treatment Permutations

### Scenario `SC-13`: Account Tombstone PII Exposure (`rule_15`)
* **Signature:** An internal tombstone record preserves the stable `user_id` (which is permitted), but still retains direct PII (`name`, `email`, `phone`, `email_hash`).
* **Example (`case_32` - Addo Kofi):**
  - In `evidence_51` (`customer_data_snapshot_bundle_20260915.json`), `tombstone_9178` contains customer personal details.
* **Evaluation:**
  - Finding: `REPORT_EXPOSED_PII` on `tombstone_9178` (`identity_service`).
  - Remediation: `REDACT_RECORD` (`identity_service`).
  - Verification: `VERIFY_RECORD_ABSENT` (`account_service`), `VERIFY_RECORD_PRESENT` (`security_service`), `VERIFY_RECORD_REDACTED` (`tombstone_9178`).
* **Expected Output:**
  ```csv
  case_32,INCOMPLETE,"[{""step_no"":1,""phase"":""FINDING"",""system_id"":""identity_service"",""resource_id"":""tombstone_9178"",""operation"":""REPORT_EXPOSED_PII"",""state"":""PRESENT"",""evidence_id"":""evidence_51""},{""step_no"":2,""phase"":""REMEDIATION"",""system_id"":""identity_service"",""resource_id"":""tombstone_9178"",""operation"":""REDACT_RECORD"",""state"":""REDACTED"",""evidence_id"":""""},{""step_no"":3,""phase"":""VERIFICATION"",""system_id"":""account_service"",""resource_id"":""account_8858"",""operation"":""VERIFY_RECORD_ABSENT"",""state"":""ABSENT"",""evidence_id"":""""},{""step_no"":4,""phase"":""VERIFICATION"",""system_id"":""security_service"",""resource_id"":""audit_record_7068"",""operation"":""VERIFY_RECORD_PRESENT"",""state"":""PRESENT"",""evidence_id"":""""},{""step_no"":5,""phase"":""VERIFICATION"",""system_id"":""identity_service"",""resource_id"":""tombstone_9178"",""operation"":""VERIFY_RECORD_REDACTED"",""state"":""REDACTED"",""evidence_id"":""""}]"
  ```

---

### Scenario `SC-14`: Compliant Account Tombstone (`rule_15`)
* **Signature:** Tombstone preserves `user_id`, while all direct PII fields (`name`, `email`, `phone`, `email_hash`) are `null`.
* **Example (`case_31` - A. Eze):**
  - In `evidence_51`, `tombstone_440` has direct identifiers set to `null`.
* **Expected Output:**
  ```csv
  case_31,COMPLETE,"[{""step_no"":1,""phase"":""VERIFICATION"",""system_id"":""account_service"",""resource_id"":""account_4857"",""operation"":""VERIFY_RECORD_ABSENT"",""state"":""ABSENT"",""evidence_id"":""evidence_51""},{""step_no"":2,""phase"":""VERIFICATION"",""system_id"":""security_service"",""resource_id"":""audit_record_6909"",""operation"":""VERIFY_RECORD_PRESENT"",""state"":""PRESENT"",""evidence_id"":""evidence_51""},{""step_no"":3,""phase"":""VERIFICATION"",""system_id"":""identity_service"",""resource_id"":""tombstone_440"",""operation"":""VERIFY_RECORD_REDACTED"",""state"":""REDACTED"",""evidence_id"":""evidence_51""}]"
  ```

---

### Scenario `SC-15`: Retained Security Audit Log (`rule_12`)
* **Signature:** An audit log event (e.g. `IDENTITY_CHANGE_RECORDED`, `ACCOUNT_DELETION_RECORDED`) is stored within its legal retention window (`retention_until > audit_at`).
* **Evaluation:**
  - Policy requires this record to be **retained**, never deleted.
  - In verification: `VERIFY_RECORD_PRESENT` on `security_service`.

---

### Scenario `SC-16`: Backup Restore Risk (`rule_14`)
* **Signature:** A physical backup archive exists with `restore_allowed = true`. If restored, it would bring back deleted data.
* **Example (`case_09` - K. Appiah):**
  - In `evidence_93`, `backup_4978` has `restore_allowed = true`.
* **Remediation & Verification:**
  - Finding: `REPORT_RESTORE_RISK`, `backup_service`, `backup_4978`, `ACTIVE`.
  - Remediation: `BLOCK_RESTORE`, `backup_service`, `backup_4978`, `BLOCKED`.
  - Verification: `VERIFY_RESTORE_BLOCKED`, `backup_service`, `backup_4978`, `BLOCKED`.

---

### Scenario `SC-17`: Active Integration Data Flow
* **Signature:** An automated connector (e.g. `analytics_identity_bridge` or `customer_events_connector`) has `enabled = true`.
* **Example (`case_15` - Lucia Torres):**
  - In `evidence_01`, `data_flow_9846` has `enabled = true`.
* **Remediation & Verification:**
  - Finding: `REPORT_ACTIVE_DATA_FLOW`, `integration_service`, `data_flow_9846`, `ACTIVE`.
  - Remediation: `DISABLE_DATA_FLOW`, `integration_service`, `data_flow_9846`, `DISABLED`.
  - Verification: `VERIFY_DATA_FLOW_DISABLED`, `integration_service`, `data_flow_9846`, `DISABLED`.

---

### Scenario `SC-18`: Exposed Support Ticket PII (`rule_05`)
* **Signature:** Customer submitted support inquiries containing email/phone. Conversation context must remain, but customer PII must be redacted.
* **Example (`case_19` - E. Varga):**
  - In `evidence_01`, `support_9553` has `requester_email = "e.varga90@yahoo.com"`.
* **Remediation & Verification:**
  - Finding: `REPORT_EXPOSED_PII`, `support_platform`, `support_9553`, `PRESENT`.
  - Remediation: `REDACT_RECORD`, `support_platform`, `support_9553`, `REDACTED`.
  - Verification: `VERIFY_RECORD_REDACTED`, `support_platform`, `support_9553`, `REDACTED`.

---

### Scenario `SC-19`: Unanonymized Analytics Profile (`rule_07`)
* **Signature:** Profile in `analytics_platform` contains email or phone instead of cohort-only aggregation.
* **Example (`case_22` - Seoyeon Han):**
  - In `evidence_05`, `analytics_4440` has customer email.
* **Remediation & Verification:**
  - Finding: `REPORT_EXPOSED_PII`, `analytics_platform`, `analytics_4440`, `PRESENT`.
  - Remediation: `ANONYMIZE_RECORD`, `analytics_platform`, `analytics_4440`, `ANONYMIZED`.
  - Verification: `VERIFY_RECORD_ANONYMIZED`, `analytics_platform`, `analytics_4440`, `ANONYMIZED`.

---

### Scenario `SC-20`: Residual Search Index Record (`rule_03`)
* **Signature:** Customer directory search index still yields documents for the customer email.
* **Example (`case_06` - Jonas Berg):**
  - In `evidence_57`, index query hits `search_001`.
* **Remediation & Verification:**
  - Finding: `REPORT_REMAINING_RECORD`, `search_service`, `search_001`, `PRESENT`.
  - Remediation: `DELETE_RECORD`, `search_service`, `search_001`, `ABSENT`.
  - Verification: `VERIFY_RECORD_ABSENT`, `search_service`, `search_001`, `ABSENT`.

---

### Scenario `SC-21`: Downloadable User Export Leftover (`rule_09`)
* **Signature:** Prior data export (`.zip`) created via "download your data" remains stored in an object bucket.
* **Example (`case_08` - Gabriel Costa):**
  - In `evidence_59`, `export_001` is still active.
* **Remediation & Verification:**
  - Finding: `REPORT_REMAINING_RECORD`, `export_service`, `export_001`, `PRESENT`.
  - Remediation: `DELETE_RECORD`, `export_service`, `export_001`, `ABSENT`.
  - Verification: `VERIFY_RECORD_ABSENT`, `export_service`, `export_001`, `ABSENT`.

---

## 5. Complex Multi-Violation Cascades & Ordering Rules

### Scenario `SC-22`: Multi-System Cascade with Strict Dependency Ordering
* **Signature:** A case simultaneously exhibits an active data flow, a remaining search record, exposed support PII, and exposed analytics PII.
* **Example (`case_11` - Tomasz Novak):**
  - Active data flow: `data_flow_9522` (`integration_service`)
  - Search record: `search_052` (`search_service`)
  - Support ticket: `support_864` (`support_platform`)
  - Analytics profile: `analytics_2034` (`analytics_platform`)
  - Retained security record: `audit_record_9394` (`security_service`)
  - Primary account: `account_4248` (`account_service`)
* **Strict Phase & Operation Ordering Sequence:**
  1. **Findings (Operation Order & Alphabetical Tie-Breaking):**
     - Step 1: `REPORT_REMAINING_RECORD` on `search_052` (`search_service`)
     - Step 2: `REPORT_EXPOSED_PII` on `analytics_2034` (`analytics_platform`)
     - Step 3: `REPORT_EXPOSED_PII` on `support_864` (`support_platform`)
     - Step 4: `REPORT_ACTIVE_DATA_FLOW` on `data_flow_9522` (`integration_service`)
  2. **Remediation (Dependency Order: Inactive Flows First!):**
     - Step 5: `DISABLE_DATA_FLOW` on `data_flow_9522` (`integration_service`)
     - Step 6: `DELETE_RECORD` on `search_052` (`search_service`)
     - Step 7: `REDACT_RECORD` on `support_864` (`support_platform`)
     - Step 8: `ANONYMIZE_RECORD` on `analytics_2034` (`analytics_platform`)
  3. **Verification (Post-Remediation Check):**
     - Step 9: `VERIFY_RECORD_ABSENT` on `account_4248` (`account_service`)
     - Step 10: `VERIFY_RECORD_ABSENT` on `search_052` (`search_service`)
     - Step 11: `VERIFY_RECORD_PRESENT` on `audit_record_9394` (`security_service`)
     - Step 12: `VERIFY_RECORD_REDACTED` on `support_864` (`support_platform`)
     - Step 13: `VERIFY_RECORD_ANONYMIZED` on `analytics_2034` (`analytics_platform`)
     - Step 14: `VERIFY_DATA_FLOW_DISABLED` on `data_flow_9522` (`integration_service`)
* **Evidence Citation Rule:** Steps 1-4 cite `evidence_03`. Steps 5-14 describe prospective remediation and post-remediation checks, so `evidence_id = ""` strictly.

---

### Scenario `SC-23`: Marketing Opt-In Profile Residual in Analytics Streams (`rule_10`)
* **Signature:** An analytics logging stream (`service_events_*.log`) captures marketing contact lookups where `email_opt_in=true`. Under Policy Rule 10 (`MARKETING_PROFILE, Always, DELETE`), opt-in and marketing profiles must be deleted rather than merely anonymized.
* **Example (`case_12` - Minjun Kim):**
  - Observed in `evidence_01` (`service_events_ap_south_20260915.log`): `analytics_9914` with `email_opt_in=true`.
* **Remediation & Verification:**
  - Finding: `REPORT_REMAINING_RECORD`, `analytics_platform`, `analytics_9914`, `PRESENT`, citing `evidence_01`.
  - Remediation: `DELETE_RECORD`, `analytics_platform`, `analytics_9914`, `ABSENT`, `evidence_id = ""`.
  - Verification: `VERIFY_RECORD_ABSENT`, `analytics_platform`, `analytics_9914`, `ABSENT`, `evidence_id = ""`.

---

### Scenario `SC-24`: Support File Attachment Exclusive to Deletion Subject (`rule_06`)
* **Signature:** A support ticket attachment (e.g. uploaded ID scan, receipt, or proof of address) belongs exclusively to the deletion subject. Unlike conversation messages that contain shared context (`rule_05` &rarr; `REDACT`), attachments must be completely deleted (`rule_06` &rarr; `DELETE`).
* **Example (`case_13` - Noor Khalil):**
  - Recorded in `customer_account_handover_20261001.txt`: `support_4218` under category `SUPPORT_ATTACHMENT` with status `FOUND`.
* **Remediation & Verification:**
  - Finding: `REPORT_REMAINING_RECORD`, `support_platform`, `support_4218`, `PRESENT`, citing `evidence_03`.
  - Remediation: `DELETE_RECORD`, `support_platform`, `support_4218`, `ABSENT`, `evidence_id = ""`.
  - Verification: `VERIFY_RECORD_ABSENT`, `support_platform`, `support_4218`, `ABSENT`, `evidence_id = ""`.

---

### Scenario `SC-25`: Database Read Replica & Failover Ghost Records
* **Signature:** Primary transactional tables have successfully purged customer profiles, but secondary read replicas or regional failover dumps (`customer_data_read_replica_*.sql`) retain full profile records or search index records.
* **Example (`case_16` - Diya K):**
  - In `evidence_05` (`customer_data_read_replica_20260921.sql`), `INSERT INTO "customer_data_read_replica"` contains active entries for `account_994` and `search_1007`.
* **Remediation & Verification:**
  - Finding: `REPORT_REMAINING_RECORD` on `account_994` and `search_1007`, citing `evidence_05`.
  - Remediation: `DELETE_RECORD` on both resources, `evidence_id = ""`.
  - Verification: `VERIFY_RECORD_ABSENT` on both resources, `evidence_id = ""`.

---

### Scenario `SC-26`: Multi-Service Snapshot Assurance Verification (`COMPLETE` Case)
* **Signature:** An account deletion request was fully executed by the deletion worker. The audit snapshot bundle (`customer_data_snapshot_bundle_*.json`) or service resource export confirms that:
  - Account service profile lookup returns 404 / absent.
  - Retained security audit event is intact within legal retention period.
  - Analytics profile is stripped of user identifiers (cohort metrics retained).
  - Support ticket messages are redacted (`[REDACTED]`).
  - Active integration connectors are stopped (`enabled = false`).
  - Backup archive restore access is blocked (`restore_allowed = false`).
* **Example (`case_21` - Amara Okeke & `case_31` - Amara Eze):**
  - `case_31` verified against `evidence_51`:
    1. Step 1: `VERIFY_RECORD_ABSENT`, `account_service`, `account_4857`, `evidence_51`
    2. Step 2: `VERIFY_RECORD_PRESENT`, `security_service`, `audit_record_6909`, `evidence_51`
    3. Step 3: `VERIFY_RECORD_REDACTED`, `identity_service`, `tombstone_440`, `evidence_51`
  - Verdict: `COMPLETE`. Only evidence-backed verification steps are emitted.

