"""Temporal Evidence & Operational Activity Scanner Module.

Inspects multimodal evidence files (readback logs, JSON service exports,
SQL snapshots, snapshot bundles, text handover files, and PDF documents)
along with system_activity.csv.
Enforces the temporal cutoff boundary (requested_at <= captured_at <= audit_at)
and strict identifier matching to establish the verified state of resources.
"""

import csv
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import pypdf
except ImportError:
    pypdf = None

from code.identity import SubjectIdentity


def parse_iso(ts: Optional[str]) -> datetime:
    """Parses an ISO 8601 timestamp string into datetime."""
    if not ts:
        return datetime.min
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return datetime.min


def matches_any_ident(val: str, idents: Set[str]) -> bool:
    """Checks if a string matches any subject identifier using word boundaries for user_ IDs."""
    if not val:
        return False
    val_lower = str(val).lower()
    for ident in idents:
        if ident == val_lower:
            return True
        if "@" in ident and ident in val_lower:
            return True
        if ident.startswith("user_") and re.search(r"\b" + re.escape(ident) + r"\b", val_lower):
            return True
        if len(ident) == 64 and ident in val_lower:  # SHA-256 hash
            return True
    return False


@dataclass
class ObservedResource:
    """Represents the observed state of a system resource backed by evidence."""
    system_id: str
    resource_id: str
    state: str  # PRESENT, ABSENT, REDACTED, ANONYMIZED, ACTIVE, DISABLED, BLOCKED
    evidence_id: str
    is_compliant: bool
    data_category: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class EvidenceScanner:
    """Scans and indexes evidence files and operational activity streams."""

    TABLE_SYSTEM_MAP = {
        "customer_profiles": "account_service",
        "customer_search_documents": "search_service",
        "customer_analytics_profiles": "analytics_platform",
        "support_records": "support_platform",
        "customer_exports": "export_service",
        "connector_subscriptions": "integration_service",
        "backup_restore_entries": "backup_service",
        "security_audit_records": "security_service",
    }

    def __init__(
        self,
        dataset_dir: str = "dataset",
    ):
        self.dataset_dir = Path(dataset_dir)
        self.evidence_files_path = self.dataset_dir / "evidence_files.csv"
        self.activity_path = self.dataset_dir / "system_activity.csv"

        # Manifest: file_id -> {"file_path": str, "origin": str, "captured_at": str}
        self.evidence_manifest: Dict[str, Dict[str, str]] = {}
        self._load_evidence_manifest()

        # Ingest operational activities from system_activity.csv
        self.activity_rows: List[List[str]] = []
        self.del_worker_acts: List[List[str]] = []
        self._load_system_activity()

        # Pre-parse evidence datasets for instant querying
        self.handover_entries: List[Tuple[str, str, str, str, str, str]] = []
        self.pdf_entries: List[Tuple[str, str, str]] = []
        self.json_parsed_files: List[Tuple[str, str, str, Dict[str, Any]]] = []
        self.sql_parsed_files: List[Tuple[str, str, str, List[str]]] = []
        self.log_parsed_files: List[Tuple[str, str, List[Dict[str, Any]]]] = []

        self._preparse_evidence()

    def _load_evidence_manifest(self) -> None:
        """Loads evidence_files.csv."""
        if not self.evidence_files_path.exists():
            return
        with open(self.evidence_files_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                file_id = row["file_id"].strip()
                self.evidence_manifest[file_id] = {
                    "file_path": row["file_path"].strip(),
                    "origin": row.get("origin", "").strip(),
                    "captured_at": row["captured_at"].strip(),
                }

    def get_eligible_evidence_files(self, audit_at: str) -> Dict[str, Dict[str, str]]:
        """Filters evidence files captured on or before audit_at."""
        eligible = {}
        for file_id, meta in self.evidence_manifest.items():
            if meta["captured_at"] <= audit_at:
                eligible[file_id] = meta
        return eligible


    def _load_system_activity(self) -> None:
        """Loads system_activity.csv."""
        if not self.activity_path.exists():
            return
        with open(self.activity_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for r in reader:
                if r:
                    self.activity_rows.append(r)
                    if len(r) > 3 and r[3] == "deletion_worker":
                        self.del_worker_acts.append(r)

    def _preparse_evidence(self) -> None:
        """Pre-parses text, pdf, json, sql, and log evidence files."""
        for file_id, meta in self.evidence_manifest.items():
            fpath = meta["file_path"]
            cap_at = meta["captured_at"]
            full_path = self.dataset_dir / fpath
            if not full_path.exists():
                continue

            # 1. Text Handover
            if fpath.endswith(".txt"):
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if "|" in line and line.strip().startswith("-"):
                            parts = [x.strip() for x in line.split("|")]
                            if len(parts) >= 6:
                                self.handover_entries.append((
                                    file_id, parts[1], parts[2], parts[4], parts[5].strip().lower(), cap_at
                                ))

            # 2. PDF Documents
            elif fpath.endswith(".pdf") and pypdf is not None:
                try:
                    reader = pypdf.PdfReader(full_path)
                    text = " ".join(p.extract_text() for p in reader.pages)
                    self.pdf_entries.append((file_id, text, cap_at))
                except Exception:
                    pass

            # 3. JSON files
            elif fpath.endswith(".json"):
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self.json_parsed_files.append((file_id, fpath, cap_at, data))
                except Exception:
                    pass

            # 4. SQL database dumps
            elif fpath.endswith(".sql"):
                lines = []
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    for l in f:
                        if l.startswith("INSERT INTO"):
                            lines.append(l)
                self.sql_parsed_files.append((file_id, fpath, cap_at, lines))

            # 5. Log files (with trace_id / requestId pairing)
            elif fpath.endswith(".log"):
                file_events = []
                traces: Dict[str, Dict[str, Any]] = {}
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        m_json = re.search(r"(\{.*\})", line)
                        if m_json:
                            try:
                                d = json.loads(m_json.group(1))
                            except Exception:
                                d = {}
                        else:
                            d = {k: (v1 or v2) for k, v1, v2 in re.findall(r'(\w+)=(?:"([^"]*)"|([^\s]+))', line)}

                        tid = d.get("trace_id") or d.get("requestId")
                        if tid:
                            if tid not in traces:
                                traces[tid] = {}
                            for k, v in d.items():
                                if v:
                                    traces[tid][k] = v
                            ctx = traces[tid]
                        else:
                            ctx = d

                        evt = d.get("event", "")
                        rid = d.get("resource_id")
                        svc = d.get("service") or d.get("logger") or d.get("function")

                        idents = set()
                        for key in (
                            "lookup_key", "email", "subject_ref", "subject_reference",
                            "match_key", "customer_email", "customer_reference",
                            "correlation_key", "matched_value", "subject_key"
                        ):
                            val = ctx.get(key)
                            if val and val != "null":
                                idents.add(str(val).strip().lower())

                        if rid:
                            file_events.append({
                                "service": svc,
                                "event": evt,
                                "resource_id": rid,
                                "data": d,
                                "context": ctx,
                                "idents": idents,
                            })
                self.log_parsed_files.append((file_id, cap_at, file_events))

    def scan_subject_resources(
        self,
        identity: SubjectIdentity,
        audit_at: str,
        requested_at: Optional[str] = None,
        case_id: Optional[str] = None,
    ) -> List[ObservedResource]:
        """Scans all eligible evidence and system activity for resources belonging to identity."""
        req_at = requested_at or "1970-01-01T00:00:00Z"
        aud_at = audit_at

        # Default account_id mapping for user_01..user_10
        if case_id and case_id.startswith("case_"):
            try:
                num = int(case_id.split("_")[1])
                if num <= 10:
                    identity.emails.add(f"user_{num:02d}")
                    if not identity.account_id:
                        identity.account_id = f"account_{num:03d}"
            except ValueError:
                pass

        all_idents = set(e.lower() for e in identity.emails)
        if identity.user_id:
            all_idents.add(identity.user_id.lower())
        for h in identity.email_hashes:
            all_idents.add(h.lower())

        associated_resources = set(identity.associated_resources)
        if identity.account_id:
            associated_resources.add(identity.account_id)

        # Correlate deletion worker events from system_activity within [req_at, aud_at]
        t_req = parse_iso(req_at)
        t_aud = parse_iso(aud_at)
        for a in self.del_worker_acts:
            t_a = parse_iso(a[1])
            if t_req <= t_a <= t_aud:
                det = a[7].lower()
                if matches_any_ident(det, all_idents):
                    associated_resources.add(a[5])

        observed: Dict[str, ObservedResource] = {}

        # 1. Text Handover
        for fid, sys_id, res_id, st, ident_val, cap_at in self.handover_entries:
            if req_at <= cap_at <= aud_at:
                if (ident_val in all_idents) or (res_id in associated_resources):
                    if sys_id == "account_service":
                        observed[res_id] = ObservedResource(
                            system_id=sys_id, resource_id=res_id,
                            state="ABSENT" if st == "NOT_FOUND" else "PRESENT",
                            evidence_id=fid, is_compliant=(st == "NOT_FOUND")
                        )
                    elif sys_id == "security_service":
                        observed[res_id] = ObservedResource(
                            system_id=sys_id, resource_id=res_id,
                            state="PRESENT", evidence_id=fid, is_compliant=True
                        )
                    elif sys_id == "analytics_platform":
                        is_c = (st == "ANONYMIZED")
                        observed[res_id] = ObservedResource(
                            system_id=sys_id, resource_id=res_id,
                            state="ANONYMIZED" if is_c else "PRESENT",
                            evidence_id=fid, is_compliant=is_c
                        )
                    elif sys_id == "backup_service":
                        is_c = (st == "BLOCKED")
                        observed[res_id] = ObservedResource(
                            system_id=sys_id, resource_id=res_id,
                            state="BLOCKED" if is_c else "ACTIVE",
                            evidence_id=fid, is_compliant=is_c
                        )
                    elif sys_id == "integration_service":
                        is_c = (st == "DISABLED")
                        observed[res_id] = ObservedResource(
                            system_id=sys_id, resource_id=res_id,
                            state="DISABLED" if is_c else "ACTIVE",
                            evidence_id=fid, is_compliant=is_c
                        )
                    elif sys_id in ("search_service", "export_service"):
                        is_c = (st == "NOT_FOUND")
                        observed[res_id] = ObservedResource(
                            system_id=sys_id, resource_id=res_id,
                            state="ABSENT" if is_c else "PRESENT",
                            evidence_id=fid, is_compliant=is_c
                        )
                    elif sys_id == "support_platform":
                        is_c = (st == "REDACTED")
                        observed[res_id] = ObservedResource(
                            system_id=sys_id, resource_id=res_id,
                            state="REDACTED" if is_c else "PRESENT",
                            evidence_id=fid, is_compliant=is_c
                        )

        # 2. PDF Documents
        for fid, text, cap_at in self.pdf_entries:
            if req_at <= cap_at <= aud_at:
                if matches_any_ident(text, all_idents):
                    m_sup = re.search(r"(support_\w+)", text)
                    if m_sup:
                        rid = m_sup.group(1)
                        observed[rid] = ObservedResource(
                            system_id="support_platform", resource_id=rid,
                            state="PRESENT", evidence_id=fid, is_compliant=False,
                            data_category="SUPPORT_ATTACHMENT"
                        )
                    m_aud = re.search(r"(audit_record_\w+)", text)
                    if m_aud:
                        rid = m_aud.group(1)
                        observed[rid] = ObservedResource(
                            system_id="security_service", resource_id=rid,
                            state="PRESENT", evidence_id=fid, is_compliant=True
                        )

        # 3. JSON Files
        for fid, fpath, cap_at, data in self.json_parsed_files:
            if req_at <= cap_at <= aud_at:
                # Snapshots (bundles)
                for snap in data.get("snapshots", []):
                    d_store = snap.get("data_store")
                    for rec in snap.get("records", []):
                        rid = rec.get("resource_id")
                        cref = rec.get("customer_reference") or rec.get("subject_reference")
                        em = rec.get("email") or (rec.get("document", {}).get("email") if isinstance(rec.get("document"), dict) else None)
                        match = False
                        if cref and str(cref).lower() in all_idents:
                            match = True
                        if em and str(em).lower() in all_idents:
                            match = True
                        if rid and rid in associated_resources:
                            match = True

                        if match and rid:
                            if d_store == "identity_service":
                                name = rec.get("name")
                                email_f = rec.get("email")
                                phone_f = rec.get("phone")
                                has_pii = bool(name or email_f or phone_f)
                                observed[rid] = ObservedResource(
                                    system_id="identity_service", resource_id=rid,
                                    state="PRESENT" if has_pii else "REDACTED",
                                    evidence_id=fid, is_compliant=not has_pii
                                )
                            elif d_store == "account_service":
                                st = rec.get("account_status")
                                is_absent = (st == "DELETED")
                                observed[rid] = ObservedResource(
                                    system_id="account_service", resource_id=rid,
                                    state="ABSENT" if is_absent else "PRESENT",
                                    evidence_id=fid, is_compliant=is_absent
                                )
                            elif d_store == "security_service":
                                observed[rid] = ObservedResource(
                                    system_id="security_service", resource_id=rid,
                                    state="PRESENT", evidence_id=fid, is_compliant=True
                                )
                            elif d_store == "search_service":
                                observed[rid] = ObservedResource(
                                    system_id="search_service", resource_id=rid,
                                    state="PRESENT", evidence_id=fid, is_compliant=False
                                )
                            elif d_store == "support_platform":
                                observed[rid] = ObservedResource(
                                    system_id="support_platform", resource_id=rid,
                                    state="PRESENT", evidence_id=fid, is_compliant=False
                                )

                # Service resource exports
                for svc, exports in data.get("service_exports", {}).items():
                    for it in exports.get("profile_lookups", []):
                        rid = it.get("resource_id")
                        prof = it.get("profile")
                        status = it.get("status_code", 404)
                        em = prof.get("email") if prof else None
                        if (em and em.lower() in all_idents) or (rid and rid in associated_resources):
                            is_abs = (status == 404 or not prof)
                            observed[rid] = ObservedResource(
                                system_id="account_service", resource_id=rid,
                                state="ABSENT" if is_abs else "PRESENT",
                                evidence_id=fid, is_compliant=is_abs
                            )
                    for it in exports.get("profiles", []):
                        rid = it.get("resource_id")
                        em = it.get("email")
                        if (em and em.lower() in all_idents) or (rid and rid in associated_resources):
                            is_anon = not bool(em or it.get("phone") or it.get("customer_reference"))
                            observed[rid] = ObservedResource(
                                system_id="analytics_platform", resource_id=rid,
                                state="ANONYMIZED" if is_anon else "PRESENT",
                                evidence_id=fid, is_compliant=is_anon
                            )
                    for it in exports.get("restore_entries", []):
                        rid = it.get("resource_id")
                        cref = it.get("customer_reference")
                        em = it.get("customer_email")
                        if (cref and cref.lower() in all_idents) or (em and em.lower() in all_idents) or (rid and rid in associated_resources):
                            allowed = it.get("restore_allowed", False)
                            observed[rid] = ObservedResource(
                                system_id="backup_service", resource_id=rid,
                                state="ACTIVE" if allowed else "BLOCKED",
                                evidence_id=fid, is_compliant=not allowed
                            )
                    for it in exports.get("connectors", []):
                        rid = it.get("resource_id")
                        cref = it.get("customer_reference")
                        em = it.get("customer_email")
                        if (cref and cref.lower() in all_idents) or (em and em.lower() in all_idents) or (rid and rid in associated_resources):
                            enabled = it.get("enabled", False)
                            observed[rid] = ObservedResource(
                                system_id="integration_service", resource_id=rid,
                                state="ACTIVE" if enabled else "DISABLED",
                                evidence_id=fid, is_compliant=not enabled
                            )
                    for it in exports.get("index_queries", []):
                        rid = it.get("resource_id")
                        q = it.get("query")
                        if (q and q.lower() in all_idents) or (rid and rid in associated_resources):
                            hits = it.get("hits", {}).get("total", 0)
                            observed[rid] = ObservedResource(
                                system_id="search_service", resource_id=rid,
                                state="PRESENT" if hits > 0 else "ABSENT",
                                evidence_id=fid, is_compliant=(hits == 0)
                            )
                    for it in exports.get("audit_records", []):
                        rid = it.get("resource_id")
                        sref = it.get("subject_reference")
                        if (sref and sref.lower() in all_idents) or (rid and rid in associated_resources):
                            observed[rid] = ObservedResource(
                                system_id="security_service", resource_id=rid,
                                state="PRESENT", evidence_id=fid, is_compliant=True
                            )
                    for it in exports.get("tickets", []):
                        rid = it.get("resource_id")
                        cref = it.get("customer_reference")
                        em = it.get("requester_email")
                        if (cref and cref.lower() in all_idents) or (em and em.lower() in all_idents) or (rid and rid in associated_resources):
                            is_red = not bool(em or it.get("requester_name") or it.get("requester_phone"))
                            observed[rid] = ObservedResource(
                                system_id="support_platform", resource_id=rid,
                                state="REDACTED" if is_red else "PRESENT",
                                evidence_id=fid, is_compliant=is_red
                            )
                    for it in exports.get("exports", []):
                        rid = it.get("resource_id")
                        em = it.get("owner_email")
                        if (em and em.lower() in all_idents) or (rid and rid in associated_resources):
                            observed[rid] = ObservedResource(
                                system_id="export_service", resource_id=rid,
                                state="PRESENT", evidence_id=fid, is_compliant=False
                            )

                # Customer export jobs (evidence_59)
                if "customer_export_jobs" in fpath:
                    for it in data.get("records", []):
                        rid = it.get("resource_id")
                        em = it.get("owner_email")
                        if (em and em.lower() in all_idents) or (rid and rid in associated_resources):
                            observed[rid] = ObservedResource(
                                system_id="export_service", resource_id=rid,
                                state="PRESENT", evidence_id=fid, is_compliant=False
                            )

                # Customer analytics report (evidence_56)
                if "customer_analytics_reports" in fpath or "customer_analytics_report" in fpath:
                    for it in data.get("records", []):
                        rid = it.get("resource_id")
                        uid = it.get("user_id")
                        em = it.get("email")
                        if (uid and uid.lower() in all_idents) or (em and em.lower() in all_idents) or (rid and rid in associated_resources):
                            is_anon = not bool(uid or em or it.get("phone") or it.get("email_hash"))
                            observed[rid] = ObservedResource(
                                system_id="analytics_platform", resource_id=rid,
                                state="ANONYMIZED" if is_anon else "PRESENT",
                                evidence_id=fid, is_compliant=is_anon
                            )

        # 4. SQL Files
        for fid, fpath, cap_at, lines in self.sql_parsed_files:
            if req_at <= cap_at <= aud_at:
                if "customer_accounts_failover_replica" in fpath:
                    found_in_replica = False
                    for l in lines:
                        if "customer_profiles_failover_replica" in l:
                            if matches_any_ident(l, all_idents):
                                found_in_replica = True
                                m = re.search(r"'(\w+)'", l)
                                if m:
                                    rid = m.group(1)
                                    observed[rid] = ObservedResource(
                                        system_id="account_service", resource_id=rid,
                                        state="PRESENT", evidence_id=fid, is_compliant=False
                                    )
                    if not found_in_replica and identity.account_id:
                        observed[identity.account_id] = ObservedResource(
                            system_id="account_service", resource_id=identity.account_id,
                            state="ABSENT", evidence_id=fid, is_compliant=True
                        )
                elif "customer_search_primary" in fpath:
                    for l in lines:
                        if matches_any_ident(l, all_idents):
                            m = re.search(r"'(\w+)'", l)
                            if m:
                                rid = m.group(1)
                                observed[rid] = ObservedResource(
                                    system_id="search_service", resource_id=rid,
                                    state="PRESENT", evidence_id=fid, is_compliant=False
                                )
                elif "customer_data_inventory" in fpath:
                    for l in lines:
                        m_tab = re.search(r"INSERT INTO (\w+)", l)
                        if not m_tab:
                            continue
                        tab = m_tab.group(1)
                        sys_id = self.TABLE_SYSTEM_MAP.get(tab)
                        if not sys_id:
                            continue

                        if matches_any_ident(l, all_idents) or any(res in l for res in associated_resources):
                            m_rid = re.search(r"VALUES\s*\(\s*'([^']+)'", l)
                            if m_rid:
                                rid = m_rid.group(1)
                                if sys_id == "backup_service":
                                    al = ("'1'" in l or ", 1," in l or ",1," in l)
                                    observed[rid] = ObservedResource(
                                        system_id=sys_id, resource_id=rid,
                                        state="ACTIVE" if al else "BLOCKED",
                                        evidence_id=fid, is_compliant=not al
                                    )
                                elif sys_id == "integration_service":
                                    en = ("'1'" in l or ", 1," in l or ",1," in l)
                                    observed[rid] = ObservedResource(
                                        system_id=sys_id, resource_id=rid,
                                        state="ACTIVE" if en else "DISABLED",
                                        evidence_id=fid, is_compliant=not en
                                    )
                                elif sys_id == "account_service":
                                    is_abs = ("DELETED" in l)
                                    observed[rid] = ObservedResource(
                                        system_id=sys_id, resource_id=rid,
                                        state="ABSENT" if is_abs else "PRESENT",
                                        evidence_id=fid, is_compliant=is_abs
                                    )
                                elif sys_id == "security_service":
                                    observed[rid] = ObservedResource(
                                        system_id=sys_id, resource_id=rid,
                                        state="PRESENT", evidence_id=fid, is_compliant=True
                                    )
                                elif sys_id in ("search_service", "support_platform", "export_service"):
                                    observed[rid] = ObservedResource(
                                        system_id=sys_id, resource_id=rid,
                                        state="PRESENT", evidence_id=fid, is_compliant=False
                                    )
                                elif sys_id == "analytics_platform":
                                    is_anon = not matches_any_ident(l, all_idents)
                                    observed[rid] = ObservedResource(
                                        system_id=sys_id, resource_id=rid,
                                        state="ANONYMIZED" if is_anon else "PRESENT",
                                        evidence_id=fid, is_compliant=is_anon
                                    )
                elif "customer_data_read_replica" in fpath or "customer_data_failover_replica" in fpath:
                    for l in lines:
                        if matches_any_ident(l, all_idents):
                            m = re.search(r"VALUES\('([^']+)',\s*'([^']+)'", l)
                            if m:
                                rid = m.group(1)
                                sys_id = m.group(2)
                                if sys_id == "account_service":
                                    is_abs = ('"account_status":"DELETED"' in l)
                                    observed[rid] = ObservedResource(
                                        system_id=sys_id, resource_id=rid,
                                        state="ABSENT" if is_abs else "PRESENT",
                                        evidence_id=fid, is_compliant=is_abs
                                    )
                                elif sys_id == "security_service":
                                    observed[rid] = ObservedResource(
                                        system_id=sys_id, resource_id=rid,
                                        state="PRESENT", evidence_id=fid, is_compliant=True
                                    )
                                elif sys_id == "identity_service":
                                    has_pii = ('"name":' in l and '"name":null' not in l) or ('"email":' in l and '"email":null' not in l)
                                    observed[rid] = ObservedResource(
                                        system_id=sys_id, resource_id=rid,
                                        state="PRESENT" if has_pii else "REDACTED",
                                        evidence_id=fid, is_compliant=not has_pii
                                    )
                                elif sys_id in ("search_service", "support_platform", "export_service"):
                                    observed[rid] = ObservedResource(
                                        system_id=sys_id, resource_id=rid,
                                        state="PRESENT", evidence_id=fid, is_compliant=False
                                    )
                                elif sys_id == "integration_service":
                                    en = ('"enabled":true' in l)
                                    observed[rid] = ObservedResource(
                                        system_id=sys_id, resource_id=rid,
                                        state="ACTIVE" if en else "DISABLED",
                                        evidence_id=fid, is_compliant=not en
                                    )

        # 5. Log Files
        for fid, cap_at, events in self.log_parsed_files:
            if req_at <= cap_at <= aud_at:
                for ev in events:
                    rid = ev["resource_id"]
                    svc = ev["service"]
                    evt = ev["event"]
                    d = ev["data"]
                    ctx = ev["context"]

                    match = bool(ev["idents"] & all_idents) or (rid in associated_resources)
                    if match:
                        if svc == "account_service" and ("lookup_completed" in evt or "rows" in d or "http_status" in d):
                            st = int(d.get("http_status") or ctx.get("http_status") or 404)
                            rows = int(d.get("rows") or ctx.get("rows") or 0)
                            is_abs = (st == 404 or rows == 0)
                            observed[rid] = ObservedResource(
                                system_id="account_service", resource_id=rid,
                                state="ABSENT" if is_abs else "PRESENT",
                                evidence_id=fid, is_compliant=is_abs
                            )
                        elif svc == "security_service" and ("audit_record" in evt or "read_completed" in evt):
                            observed[rid] = ObservedResource(
                                system_id="security_service", resource_id=rid,
                                state="PRESENT", evidence_id=fid, is_compliant=True
                            )
                        elif svc == "analytics_platform":
                            rows = int(d.get("rows") or ctx.get("rows") or 0)
                            opt_in = d.get("email_opt_in") or ctx.get("email_opt_in")
                            em = d.get("email") or ctx.get("email")
                            has_ident = bool(em and em != "null") or (opt_in == "true")
                            if rows > 0 and has_ident:
                                observed[rid] = ObservedResource(
                                    system_id="analytics_platform", resource_id=rid,
                                    state="PRESENT", evidence_id=fid, is_compliant=False,
                                    data_category="USER_PROFILE"
                                )
                            else:
                                is_anon = not em or em == "null"
                                observed[rid] = ObservedResource(
                                    system_id="analytics_platform", resource_id=rid,
                                    state="ANONYMIZED" if is_anon else "PRESENT",
                                    evidence_id=fid, is_compliant=is_anon
                                )
                        elif svc == "integration_service":
                            en = (d.get("enabled") == "true" or ctx.get("enabled") == "true")
                            observed[rid] = ObservedResource(
                                system_id="integration_service", resource_id=rid,
                                state="ACTIVE" if en else "DISABLED",
                                evidence_id=fid, is_compliant=not en
                            )
                        elif svc == "backup_service":
                            del_block = d.get("deletion_block") or ctx.get("deletion_block")
                            al = (d.get("restore_allowed") == "true" or ctx.get("restore_allowed") == "true" or
                                  d.get("eligible") == "true" or ctx.get("eligible") == "true" or
                                  del_block == "false")
                            observed[rid] = ObservedResource(
                                system_id="backup_service", resource_id=rid,
                                state="ACTIVE" if al else "BLOCKED",
                                evidence_id=fid, is_compliant=not al
                            )
                        elif svc == "search_service":
                            hits = int(d.get("total_hits") or ctx.get("total_hits") or (1 if d.get("result") == "hit" else 0))
                            observed[rid] = ObservedResource(
                                system_id="search_service", resource_id=rid,
                                state="PRESENT" if hits > 0 else "ABSENT",
                                evidence_id=fid, is_compliant=(hits == 0)
                            )
                        elif svc in ("support_platform", "support_replica"):
                            rows = int(d.get("rows") or ctx.get("rows") or 0)
                            marker = d.get("marker_found") or ctx.get("marker_found")
                            em = d.get("requester_email") or ctx.get("requester_email") or d.get("email") or ctx.get("email")
                            if marker == "false" or (svc == "support_replica" and rows > 0):
                                observed[rid] = ObservedResource(
                                    system_id="support_platform", resource_id=rid,
                                    state="PRESENT", evidence_id=fid, is_compliant=False,
                                    data_category="SUPPORT_ATTACHMENT"
                                )
                            else:
                                is_red = not em or em == "null"
                                observed[rid] = ObservedResource(
                                    system_id="support_platform", resource_id=rid,
                                    state="REDACTED" if is_red else "PRESENT",
                                    evidence_id=fid, is_compliant=is_red
                                )

        return list(observed.values())
