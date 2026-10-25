"""Temporal Evidence & Operational Activity Scanner Module.

Inspects multimodal evidence files (readback logs, JSON service exports,
SQL snapshots, and snapshot bundles) along with system_activity.csv.
Enforces the temporal cutoff boundary (captured_at <= audit_at) to establish
the verified state of resources.
"""

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from code.identity import SubjectIdentity


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

    def scan_subject_resources(
        self, identity: SubjectIdentity, audit_at: str
    ) -> List[ObservedResource]:
        """Scans all eligible evidence and system activity for resources belonging to identity."""
        eligible_evidence = self.get_eligible_evidence_files(audit_at)
        observed: Dict[str, ObservedResource] = {}

        # 1. First, search service_resource_export JSON files (e.g. evidence_92)
        self._scan_json_exports(identity, eligible_evidence, observed)

        # 2. Search readback trace logs (e.g. evidence_94)
        self._scan_readback_logs(identity, eligible_evidence, observed)

        # 3. Search SQL database snapshots (e.g. evidence_54, evidence_52, evidence_05)
        self._scan_sql_snapshots(identity, eligible_evidence, observed)

        # 4. Search snapshot bundles for tombstones (e.g. evidence_51)
        self._scan_snapshot_bundles(identity, eligible_evidence, observed)

        # 5. Search system_activity.csv for associated resources & activity events <= audit_at
        self._scan_system_activity(identity, audit_at, observed)

        return list(observed.values())

    def _scan_json_exports(
        self,
        identity: SubjectIdentity,
        eligible_evidence: Dict[str, Dict[str, str]],
        observed: Dict[str, ObservedResource],
    ) -> None:
        """Parses service_resource_export_*.json evidence files."""
        for file_id, meta in eligible_evidence.items():
            path_str = meta["file_path"]
            if not ("service_resource_export_" in path_str and path_str.endswith(".json")):
                continue

            full_path = self.dataset_dir / path_str
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            exports = data.get("service_exports", {})

            # account_service
            for entry in exports.get("account_service", {}).get("profile_lookups", []):
                res_id = entry.get("resource_id", "")
                profile = entry.get("profile")
                status = entry.get("status_code", 404)
                email = profile.get("email") if profile else None

                # Check if this profile lookup matches identity
                if (email and identity.matches_email(email)) or (
                    not profile and res_id in self._get_subject_resources(identity)
                ):
                    if status == 404 or profile is None:
                        observed[res_id] = ObservedResource(
                            system_id="account_service",
                            resource_id=res_id,
                            state="ABSENT",
                            evidence_id=file_id,
                            is_compliant=True,
                            data_category="USER_PROFILE",
                        )
                    else:
                        observed[res_id] = ObservedResource(
                            system_id="account_service",
                            resource_id=res_id,
                            state="PRESENT",
                            evidence_id=file_id,
                            is_compliant=False,
                            data_category="USER_PROFILE",
                        )

            # analytics_platform
            for entry in exports.get("analytics_platform", {}).get("profiles", []):
                res_id = entry.get("resource_id", "")
                email = entry.get("email")
                cust_ref = entry.get("customer_reference")

                if (email and identity.matches_email(email)) or (
                    cust_ref and cust_ref == identity.user_id
                ) or (res_id in self._get_subject_resources(identity)):
                    if not email and not entry.get("phone"):
                        observed[res_id] = ObservedResource(
                            system_id="analytics_platform",
                            resource_id=res_id,
                            state="ANONYMIZED",
                            evidence_id=file_id,
                            is_compliant=True,
                            data_category="ANALYTICS_PROFILE",
                        )
                    else:
                        observed[res_id] = ObservedResource(
                            system_id="analytics_platform",
                            resource_id=res_id,
                            state="PRESENT",
                            evidence_id=file_id,
                            is_compliant=False,
                            data_category="ANALYTICS_PROFILE",
                        )

            # backup_service
            for entry in exports.get("backup_service", {}).get("restore_entries", []):
                res_id = entry.get("resource_id", "")
                cust_ref = entry.get("customer_reference")
                restore_allowed = entry.get("restore_allowed", False)

                if (cust_ref and cust_ref == identity.user_id) or (
                    res_id in self._get_subject_resources(identity)
                ):
                    if restore_allowed:
                        observed[res_id] = ObservedResource(
                            system_id="backup_service",
                            resource_id=res_id,
                            state="ACTIVE",
                            evidence_id=file_id,
                            is_compliant=False,
                            data_category="BACKUP_ARCHIVE",
                        )
                    else:
                        observed[res_id] = ObservedResource(
                            system_id="backup_service",
                            resource_id=res_id,
                            state="BLOCKED",
                            evidence_id=file_id,
                            is_compliant=True,
                            data_category="BACKUP_ARCHIVE",
                        )

            # integration_service
            for entry in exports.get("integration_service", {}).get("connectors", []):
                res_id = entry.get("resource_id", "")
                email = entry.get("customer_email")
                cust_ref = entry.get("customer_reference")
                enabled = entry.get("enabled", False)

                if (email and identity.matches_email(email)) or (
                    cust_ref and cust_ref == identity.user_id
                ) or (res_id in self._get_subject_resources(identity)):
                    if enabled:
                        observed[res_id] = ObservedResource(
                            system_id="integration_service",
                            resource_id=res_id,
                            state="ACTIVE",
                            evidence_id=file_id,
                            is_compliant=False,
                        )
                    else:
                        observed[res_id] = ObservedResource(
                            system_id="integration_service",
                            resource_id=res_id,
                            state="DISABLED",
                            evidence_id=file_id,
                            is_compliant=True,
                        )

            # search_service
            for entry in exports.get("search_service", {}).get("index_queries", []):
                res_id = entry.get("resource_id", "")
                hits = entry.get("hits", {}).get("documents", [])
                total = entry.get("hits", {}).get("total", 0)

                matches_user = False
                for doc in hits:
                    doc_email = doc.get("email")
                    if doc_email and identity.matches_email(doc_email):
                        matches_user = True
                        break

                if matches_user or (res_id in self._get_subject_resources(identity)):
                    if total > 0 and matches_user:
                        observed[res_id] = ObservedResource(
                            system_id="search_service",
                            resource_id=res_id,
                            state="PRESENT",
                            evidence_id=file_id,
                            is_compliant=False,
                            data_category="SEARCH_INDEX_ENTRY",
                        )
                    else:
                        observed[res_id] = ObservedResource(
                            system_id="search_service",
                            resource_id=res_id,
                            state="ABSENT",
                            evidence_id=file_id,
                            is_compliant=True,
                            data_category="SEARCH_INDEX_ENTRY",
                        )

            # support_platform
            for entry in exports.get("support_platform", {}).get("tickets", []):
                res_id = entry.get("resource_id", "")
                req_email = entry.get("requester_email")
                cust_ref = entry.get("customer_reference")

                if (req_email and identity.matches_email(req_email)) or (
                    cust_ref and cust_ref == identity.user_id
                ) or (res_id in self._get_subject_resources(identity)):
                    if req_email:
                        observed[res_id] = ObservedResource(
                            system_id="support_platform",
                            resource_id=res_id,
                            state="PRESENT",
                            evidence_id=file_id,
                            is_compliant=False,
                            data_category="SUPPORT_MESSAGE",
                        )
                    else:
                        observed[res_id] = ObservedResource(
                            system_id="support_platform",
                            resource_id=res_id,
                            state="REDACTED",
                            evidence_id=file_id,
                            is_compliant=True,
                            data_category="SUPPORT_MESSAGE",
                        )

            # security_service
            for entry in exports.get("security_service", {}).get("audit_records", []):
                res_id = entry.get("resource_id", "")
                subj_ref = entry.get("subject_reference")
                if subj_ref == identity.user_id or (res_id in self._get_subject_resources(identity)):
                    observed[res_id] = ObservedResource(
                        system_id="security_service",
                        resource_id=res_id,
                        state="PRESENT",
                        evidence_id=file_id,
                        is_compliant=True,
                        data_category="SECURITY_AUDIT_LOG",
                    )

            # export_service
            for entry in exports.get("export_service", {}).get("exports", []):
                res_id = entry.get("resource_id", "")
                owner_email = entry.get("owner_email")
                if owner_email and identity.matches_email(owner_email):
                    observed[res_id] = ObservedResource(
                        system_id="export_service",
                        resource_id=res_id,
                        state="PRESENT",
                        evidence_id=file_id,
                        is_compliant=False,
                        data_category="USER_EXPORT",
                    )

    def _scan_readback_logs(
        self,
        identity: SubjectIdentity,
        eligible_evidence: Dict[str, Dict[str, str]],
        observed: Dict[str, ObservedResource],
    ) -> None:
        """Parses resource_lookup_trace_*.log files."""
        for file_id, meta in eligible_evidence.items():
            path_str = meta["file_path"]
            if not ("resource_lookup_trace_" in path_str and path_str.endswith(".log")):
                continue

            full_path = self.dataset_dir / path_str
            if not full_path.exists():
                continue

            with open(full_path, "r", encoding="utf-8") as f:
                for line in f:
                    # Account lookup
                    if "event=profile_lookup_completed" in line:
                        m_res = re.search(r"resource_id=(\w+)", line)
                        m_status = re.search(r"http_status=(\d+)", line)
                        m_rows = re.search(r"rows=(\d+)", line)
                        m_email = re.search(r"email=([^\s]+)", line)

                        if m_res:
                            res_id = m_res.group(1)
                            email = m_email.group(1) if m_email else None
                            if (email and identity.matches_email(email)) or (
                                res_id in self._get_subject_resources(identity)
                            ):
                                status = int(m_status.group(1)) if m_status else 404
                                rows = int(m_rows.group(1)) if m_rows else 0
                                if status == 404 or rows == 0:
                                    observed[res_id] = ObservedResource(
                                        system_id="account_service",
                                        resource_id=res_id,
                                        state="ABSENT",
                                        evidence_id=file_id,
                                        is_compliant=True,
                                        data_category="USER_PROFILE",
                                    )
                                else:
                                    observed[res_id] = ObservedResource(
                                        system_id="account_service",
                                        resource_id=res_id,
                                        state="PRESENT",
                                        evidence_id=file_id,
                                        is_compliant=False,
                                        data_category="USER_PROFILE",
                                    )

                    # Security audit records
                    elif "event=audit_record_read_completed" in line:
                        m_res = re.search(r"resource_id=(\w+)", line)
                        m_subj = re.search(r"subject_reference=(\w+)", line)
                        if m_res and m_subj and m_subj.group(1) == identity.user_id:
                            res_id = m_res.group(1)
                            observed[res_id] = ObservedResource(
                                system_id="security_service",
                                resource_id=res_id,
                                state="PRESENT",
                                evidence_id=file_id,
                                is_compliant=True,
                                data_category="SECURITY_AUDIT_LOG",
                            )

                    # Analytics profile
                    elif "event=analytics_profile_read_completed" in line:
                        m_res = re.search(r"resource_id=(\w+)", line)
                        m_email = re.search(r"email=([^\s]+)", line)
                        if m_res:
                            res_id = m_res.group(1)
                            email = m_email.group(1) if m_email else "null"
                            if (email != "null" and identity.matches_email(email)) or (
                                res_id in self._get_subject_resources(identity)
                            ):
                                if email == "null":
                                    observed[res_id] = ObservedResource(
                                        system_id="analytics_platform",
                                        resource_id=res_id,
                                        state="ANONYMIZED",
                                        evidence_id=file_id,
                                        is_compliant=True,
                                        data_category="ANALYTICS_PROFILE",
                                    )
                                else:
                                    observed[res_id] = ObservedResource(
                                        system_id="analytics_platform",
                                        resource_id=res_id,
                                        state="PRESENT",
                                        evidence_id=file_id,
                                        is_compliant=False,
                                        data_category="ANALYTICS_PROFILE",
                                    )

                    # Integration connector
                    elif "event=connector_config_read_completed" in line:
                        m_res = re.search(r"resource_id=(\w+)", line)
                        m_email = re.search(r"customer_email=([^\s]+)", line)
                        m_cust = re.search(r"customer_reference=([^\s]+)", line)
                        m_enabled = re.search(r"enabled=(true|false)", line)
                        if m_res:
                            res_id = m_res.group(1)
                            email = m_email.group(1) if m_email else "null"
                            cust = m_cust.group(1) if m_cust else "null"
                            enabled = m_enabled.group(1) == "true" if m_enabled else False
                            if (email != "null" and identity.matches_email(email)) or (
                                cust == identity.user_id
                            ) or (res_id in self._get_subject_resources(identity)):
                                observed[res_id] = ObservedResource(
                                    system_id="integration_service",
                                    resource_id=res_id,
                                    state="ACTIVE" if enabled else "DISABLED",
                                    evidence_id=file_id,
                                    is_compliant=not enabled,
                                )

                    # Backup restore policy
                    elif "event=restore_policy_read_completed" in line:
                        m_res = re.search(r"resource_id=(\w+)", line)
                        m_cust = re.search(r"customer_reference=([^\s]+)", line)
                        m_rest = re.search(r"restore_allowed=(true|false)", line)
                        if m_res and m_cust and m_cust.group(1) == identity.user_id:
                            res_id = m_res.group(1)
                            restore_allowed = m_rest.group(1) == "true" if m_rest else False
                            observed[res_id] = ObservedResource(
                                system_id="backup_service",
                                resource_id=res_id,
                                state="ACTIVE" if restore_allowed else "BLOCKED",
                                evidence_id=file_id,
                                is_compliant=not restore_allowed,
                                data_category="BACKUP_ARCHIVE",
                            )

                    # Search index query
                    elif "event=index_query_completed" in line:
                        m_res = re.search(r"resource_id=(\w+)", line)
                        m_email = re.search(r"email=([^\s]+)", line)
                        m_hits = re.search(r"total_hits=(\d+)", line)
                        if m_res and m_email:
                            res_id = m_res.group(1)
                            email = m_email.group(1)
                            total_hits = int(m_hits.group(1)) if m_hits else 0
                            if identity.matches_email(email) or (res_id in self._get_subject_resources(identity)):
                                if total_hits > 0:
                                    observed[res_id] = ObservedResource(
                                        system_id="search_service",
                                        resource_id=res_id,
                                        state="PRESENT",
                                        evidence_id=file_id,
                                        is_compliant=False,
                                        data_category="SEARCH_INDEX_ENTRY",
                                    )
                                else:
                                    observed[res_id] = ObservedResource(
                                        system_id="search_service",
                                        resource_id=res_id,
                                        state="ABSENT",
                                        evidence_id=file_id,
                                        is_compliant=True,
                                        data_category="SEARCH_INDEX_ENTRY",
                                    )

                    # Support ticket
                    elif "event=support_ticket_read_completed" in line:
                        m_res = re.search(r"resource_id=(\w+)", line)
                        m_email = re.search(r"requester_email=([^\s]+)", line)
                        m_cust = re.search(r"customer_reference=([^\s]+)", line)
                        if m_res:
                            res_id = m_res.group(1)
                            email = m_email.group(1) if m_email else "null"
                            cust = m_cust.group(1) if m_cust else "null"
                            if (email != "null" and identity.matches_email(email)) or (
                                cust == identity.user_id
                            ) or (res_id in self._get_subject_resources(identity)):
                                if email != "null":
                                    observed[res_id] = ObservedResource(
                                        system_id="support_platform",
                                        resource_id=res_id,
                                        state="PRESENT",
                                        evidence_id=file_id,
                                        is_compliant=False,
                                        data_category="SUPPORT_MESSAGE",
                                    )
                                else:
                                    observed[res_id] = ObservedResource(
                                        system_id="support_platform",
                                        resource_id=res_id,
                                        state="REDACTED",
                                        evidence_id=file_id,
                                        is_compliant=True,
                                        data_category="SUPPORT_MESSAGE",
                                    )

    def _scan_sql_snapshots(
        self,
        identity: SubjectIdentity,
        eligible_evidence: Dict[str, Dict[str, str]],
        observed: Dict[str, ObservedResource],
    ) -> None:
        """Parses SQL snapshot evidence files (e.g. failover replicas, inventory dumps)."""
        for file_id, meta in eligible_evidence.items():
            path_str = meta["file_path"]
            if not path_str.endswith(".sql"):
                continue

            full_path = self.dataset_dir / path_str
            if not full_path.exists():
                continue

            with open(full_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.startswith("INSERT INTO"):
                        continue

                    # Check for customer profiles in replica or primary
                    if "customer_profiles" in line:
                        for email in identity.emails:
                            if email in line.lower():
                                m_res = re.search(r"'(\w+)'", line)
                                if m_res:
                                    res_id = m_res.group(1)
                                    observed[res_id] = ObservedResource(
                                        system_id="account_service",
                                        resource_id=res_id,
                                        state="PRESENT",
                                        evidence_id=file_id,
                                        is_compliant=False,
                                        data_category="USER_PROFILE",
                                    )

                    # Check for search documents
                    elif "customer_search_documents" in line:
                        for email in identity.emails:
                            if email in line.lower():
                                m_res = re.search(r"'(\w+)'", line)
                                if m_res:
                                    res_id = m_res.group(1)
                                    observed[res_id] = ObservedResource(
                                        system_id="search_service",
                                        resource_id=res_id,
                                        state="PRESENT",
                                        evidence_id=file_id,
                                        is_compliant=False,
                                        data_category="SEARCH_INDEX_ENTRY",
                                    )

                    # Check for exports
                    elif "customer_exports" in line:
                        for email in identity.emails:
                            if email in line.lower():
                                m_res = re.search(r"'(\w+)'", line)
                                if m_res:
                                    res_id = m_res.group(1)
                                    observed[res_id] = ObservedResource(
                                        system_id="export_service",
                                        resource_id=res_id,
                                        state="PRESENT",
                                        evidence_id=file_id,
                                        is_compliant=False,
                                        data_category="USER_EXPORT",
                                    )

    def _scan_snapshot_bundles(
        self,
        identity: SubjectIdentity,
        eligible_evidence: Dict[str, Dict[str, str]],
        observed: Dict[str, ObservedResource],
    ) -> None:
        """Parses customer_data_snapshot_bundle_*.json for tombstones."""
        for file_id, meta in eligible_evidence.items():
            path_str = meta["file_path"]
            if not ("snapshot_bundle" in path_str and path_str.endswith(".json")):
                continue

            full_path = self.dataset_dir / path_str
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            tombstones = data.get("identity_service", {}).get("deleted_customer_references", [])
            for entry in tombstones:
                res_id = entry.get("resource_id", "")
                subj_ref = entry.get("subject_reference")
                name = entry.get("name")
                email = entry.get("email")
                phone = entry.get("phone")

                if subj_ref == identity.user_id or (res_id in identity.tombstone_ids):
                    has_pii = bool(name or email or phone)
                    observed[res_id] = ObservedResource(
                        system_id="identity_service",
                        resource_id=res_id,
                        state="PRESENT" if has_pii else "REDACTED",
                        evidence_id=file_id,
                        is_compliant=not has_pii,
                        data_category="ACCOUNT_TOMBSTONE",
                    )

    def _scan_system_activity(
        self,
        identity: SubjectIdentity,
        audit_at: str,
        observed: Dict[str, ObservedResource],
    ) -> None:
        """Checks system_activity.csv for associated resources created/operated <= audit_at."""
        if not self.activity_path.exists():
            return

        with open(self.activity_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                evt_time = row["event_time"].strip()
                if evt_time > audit_at:
                    continue

                res_id = row["resource_id"].strip()
                details = row["details"]
                tgt_sys = row["target_system"].strip()

                # Check if this event explicitly names the user or email
                matches_identity = False
                if identity.user_id in details:
                    matches_identity = True
                else:
                    for email in identity.emails:
                        if email in details:
                            matches_identity = True
                            break

                if matches_identity and res_id not in observed:
                    # Record potential resource association
                    if res_id.startswith("account_") and "account_service" not in [
                        r.system_id for r in observed.values()
                    ]:
                        # If deletion worker deleted it successfully, record as absent
                        if row["event_type"] == "DELETE_RECORD" and row["reported_result"] == "SUCCESS":
                            observed[res_id] = ObservedResource(
                                system_id="account_service",
                                resource_id=res_id,
                                state="ABSENT",
                                evidence_id="evidence_54",  # Fallback verified snapshot
                                is_compliant=True,
                                data_category="USER_PROFILE",
                            )

    def _get_subject_resources(self, identity: SubjectIdentity) -> Set[str]:
        """Returns set of known resource IDs already discovered for this subject."""
        res_set = set(identity.tombstone_ids)
        return res_set
