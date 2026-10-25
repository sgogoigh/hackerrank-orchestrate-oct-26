# Implementation Plan - Ghost Data Still Exists Deletion-Audit Agent

Build a deterministic, evidence-grounded AI deletion-audit agent for HackerRank Orchestrate: Ghost Data Still Exists. The agent processes 518 evaluation requests, identifies non-deletion requests as `NOT_APPLICABLE`, reconstructs current and historical identity graphs, scans temporal evidence (`captured_at <= audit_at`), enforces 15 deletion policy rules, and generates strictly ordered remediation and verification steps in `output.csv`.

---

## 1. User Review Required & Guardrails

> [!IMPORTANT]
> **API Key Safety & Environment:** `GOOGLE_API_KEY` will be read directly from the runtime environment (`os.environ["GOOGLE_API_KEY"]`). No `.env` files or secret keys will ever be committed, logged, or printed in transcripts.

> [!IMPORTANT]
> **Classification Cache & Cost Control:** A local cache (`dataset/cache/intent_cache.json`) will store Gemini 3.8 Flash classifications for `request_text` to prevent redundant API calls during iterations, keep token usage minimal, and ensure 100% deterministic re-runs.

> [!NOTE]
> **Sample Integrity Guarantee:** `dataset/sample_output.csv` will be strictly read-only for evaluation and calibration. Predictions will be output to `output.csv` (both in `./` and `dataset/`).

---

## 2. Architecture & Workflow

```mermaid
graph TD
    subgraph 1. Ingestion & Filter 1
        A[deletion_requests.csv / sample_deletion_requests.csv] --> B[Multilingual Intent Classifier<br/>Gemini 3.8 Flash]
        B -->|Non-Deletion: Opt-out, Access, Rectify, Export| C[Output: case_id, NOT_APPLICABLE, []]
        B -->|Authorized Deletion| D[Authorized Deletion Cases]
    end

    subgraph 2. Identity Resolution
        D --> E[Subject Identity Resolver]
        E -->|Current Snapshot| F[(user_identities.csv)]
        E -->|Audit History| G[(user_audit_log.csv)]
        E --> H[Subject Identity Graph:<br/>user_id, all emails, names, phones, hashes, tombstones]
    end

    subgraph 3. Temporal Evidence & Activity Extraction
        H --> I[Temporal Evidence Scanner]
        I -->|Events <= audit_at| J[(system_activity.csv)]
        I -->|Files <= audit_at| K[(evidence_files.csv)]
        K --> L[Evidence Parsers:<br/>Logs, JSON exports, SQL replicas, Bundles]
    end

    subgraph 4. Deletion Rule Engine
        L & J --> M[Resource State Evaluator]
        M -->|Apply| N[(deletion_rules.csv)]
        N --> O{Any Remaining Data / Recreation Risk?}
        O -->|No Violations| P[COMPLETE Status<br/>Evidence-backed Verification]
        O -->|Violations Found| Q[INCOMPLETE Status<br/>Findings + Remediation + Future Verification]
    end

    subgraph 5. Deterministic Serialization
        P & Q --> R[Deterministic Step Sequencer<br/>Phase -> Op Sequence -> system_id -> resource_id]
        C & R --> S[output.csv<br/>518 rows sorted by case_id]
    end

    subgraph 6. Evaluation & Usage Reporting
        S --> T[Evaluation Engine<br/>code/evaluation/main.py]
        T -->|Benchmark against| U[(sample_output.csv)]
        T --> V[code/evaluation/evaluation_report.md<br/>code/evaluation/usage_report.md]
    end
```

---

## 3. Proposed Changes & Implementation Components

### Component 1: Multilingual Intent Classification (`code/classifier.py`)
- Purpose: Classify `request_text` across multiple languages (English, Spanish, French, Japanese, Korean, Portuguese, German, etc.).
- Model: `gemini-3.8-flash` via official Google Generative AI SDK / REST API.
- Prompt design: Strict structured JSON output specifying whether the user authorizes complete account deletion vs marketing opt-out, access/data inspection, data export, or detail update.
- Caching: Persist classifications in `dataset/cache/intent_cache.json`.

#### [NEW] `code/classifier.py`
```python
# code/classifier.py
import json
import os
from typing import Dict, Any

class IntentClassifier:
    """Classifies user deletion request text using Gemini 3.8 Flash."""
    def __init__(self, cache_path: str = "dataset/cache/intent_cache.json"):
        self.cache_path = cache_path
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        self.cache = self._load_cache()

    def is_deletion_request(self, case_id: str, request_text: str) -> bool:
        # Check cache first
        if case_id in self.cache:
            return self.cache[case_id]["is_deletion"]
        # Call Gemini 3.8 Flash with temperature=0.0
        ...
```

---

### Component 2: Subject Identity Resolution (`code/identity.py`)
- Purpose: Map the input `email` to all identifiers across time.
- Join logic:
  - Step 1: Look up `email` in `user_identities.csv`. If present, get `user_id`.
  - Step 2: If absent, search `user_audit_log.csv` (`old_value` and `new_value` for `field_name == 'email'`) to find the associated `user_id`.
  - Step 3: Given `user_id`, compile all current and historical emails, names, phone numbers, email hashes (SHA-256), and linked tombstone IDs (from `system_activity.csv` `LINK_RESOURCE_IDENTITY`).

#### [NEW] `code/identity.py`
```python
# code/identity.py
import csv
import hashlib
from dataclasses import dataclass, field
from typing import Set, Dict, Optional

@dataclass
class SubjectIdentity:
    user_id: str
    emails: Set[str] = field(default_factory=set)
    phones: Set[str] = field(default_factory=set)
    names: Set[str] = field(default_factory=set)
    email_hashes: Set[str] = field(default_factory=set)
    tombstone_ids: Set[str] = field(default_factory=set)

class IdentityResolver:
    ...
```

---

### Component 3: Evidence & Activity Scanner (`code/evidence_scanner.py`)
- Purpose: Filter evidence by `captured_at <= audit_at` and `event_time <= audit_at`. Parse evidence content to determine ground-truth state of each resource.
- Handlers:
  - `LogHandler`: Parses `evidence/logs/resource_lookup_trace_*.log` for profile lookups (`http_status=404` vs `200`), connector states (`enabled=true/false`), restore policies (`restore_allowed=true/false`), index queries (`result=hit` vs empty), support ticket inspections, audit records.
  - `JsonResourceHandler`: Parses `evidence/records/service_resource_export_*.json` for service lookups across `account_service`, `analytics_platform`, `backup_service`, `export_service`, `integration_service`, `search_service`, `security_service`, `support_platform`.
  - `SqlDatabaseHandler`: Parses `.sql` dumps for primary vs failover/read replicas.
  - `SnapshotBundleHandler`: Parses `customer_data_snapshot_bundle_*.json` for tombstone entries.

#### [NEW] `code/evidence_scanner.py`
```python
# code/evidence_scanner.py
from typing import Dict, List, Optional
from code.identity import SubjectIdentity

class EvidenceScanner:
    """Scans and extracts ground-truth resource states for a subject at audit_at."""
    ...
```

---

### Component 4: Deletion Rules & Step Generator (`code/auditor.py`)
- Purpose: Apply `deletion_rules.csv` (15 rules) to observed resources.
- Evaluates:
  - If any remaining records, exposed PII, active sync connectors, or restore risks exist:
    - Status = `INCOMPLETE`
    - Creates `FINDING` steps with proving `evidence_id`.
    - Creates `REMEDIATION` steps (`DISABLE_DATA_FLOW`, `BLOCK_RESTORE`, `DELETE_RECORD`, `REDACT_RECORD`, `ANONYMIZE_RECORD`) with `evidence_id = ""`.
    - Creates `VERIFICATION` steps (`VERIFY_RECORD_ABSENT`, `VERIFY_RECORD_PRESENT`, `VERIFY_RECORD_REDACTED`, `VERIFY_RECORD_ANONYMIZED`, `VERIFY_DATA_FLOW_DISABLED`, `VERIFY_RESTORE_BLOCKED`) with `evidence_id = ""`.
  - If all copies deleted/redacted/anonymized, data flows disabled, restores blocked, and required retained records present:
    - Status = `COMPLETE`
    - Creates `VERIFICATION` steps only, each citing the valid `evidence_id` proving compliant state at `audit_at`.
- Enforces strict sorting contract:
  - Phase order: `FINDING` &rarr; `REMEDIATION` &rarr; `VERIFICATION`
  - Operation order per `problem_statement.md` §6.4
  - `system_id` ASC, then `resource_id` ASC
  - Consecutive step numbering starting at `1`.

#### [NEW] `code/auditor.py`
```python
# code/auditor.py
from typing import List, Dict, Any, Tuple

class DeletionAuditor:
    """Evaluates policy rules and produces deterministic output rows."""
    ...
```

---

### Component 5: Main Entry Point (`code/main.py`)
- Reads `dataset/deletion_requests.csv` (518 cases) or `--samples` (`sample_deletion_requests.csv`).
- Runs pipeline, produces valid CSV rows, and writes to `output.csv` (at root and `dataset/output.csv`).
- Logs token usage and runtime statistics.

#### [MODIFY] `code/main.py`
```python
# code/main.py
import argparse
import sys
# Orchestrates classifier -> identity -> evidence -> auditor -> output.csv
...
```

---

### Component 6: Evaluation Suite & Reports (`code/evaluation/main.py`)
- Benchmarks predictions against `dataset/sample_output.csv`.
- Checks:
  1. Case-level accuracy (`deletion_status` match).
  2. Step-level precision, recall, and F1.
  3. Field-level accuracy for `step_no`, `phase`, `system_id`, `resource_id`, `operation`, `state`, `evidence_id`.
  4. Sequence accuracy (exact array matching).
- Automatically writes:
  - `code/evaluation/evaluation_report.md` (including 3 custom evaluation cases).
  - `code/evaluation/usage_report.md` (model calls, input/output tokens, cost breakdown).

#### [MODIFY] `code/evaluation/main.py`
```python
# code/evaluation/main.py
...
```

---

## 4. Verification Plan

### Automated Tests
1. **Sample Benchmark Verification:**
   Run the pipeline on `dataset/sample_deletion_requests.csv` and compare directly against `dataset/sample_output.csv`:
   - Must achieve 100% case status accuracy on sample requests.
   - Must achieve exact step and sequence matching on sample cases.
2. **First Filter Unit Test:**
   Verify that non-deletion cases (e.g. `case_538`) output:
   `case_538,NOT_APPLICABLE,[]`
3. **Full Dataset Execution:**
   Run `code/main.py` across all 518 cases in `dataset/deletion_requests.csv`:
   - Confirm exactly 518 output rows plus header.
   - Confirm sorted ascending by `case_id`.
   - Validate every row contains valid JSON for `steps_json`.
   - Confirm consecutive `step_no` (1, 2, ...).
4. **Evaluation Report Generation:**
   Run `code/evaluation/main.py` to produce `code/evaluation/evaluation_report.md` and `code/evaluation/usage_report.md`.

### Manual Verification
- Inspect generated `output.csv` format and sample rows.
- Verify `log.txt` contains valid per-turn entries conforming to `AGENTS.md`.
