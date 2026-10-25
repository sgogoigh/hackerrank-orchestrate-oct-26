"""Subject Identity Resolution Module.

Reconstructs complete current and historical identity graphs for users,
connecting primary emails, historical aliases, names, phone numbers,
SHA-256 email hashes, and linked account tombstone identifiers.
"""

import csv
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class SubjectIdentity:
    """Represents the complete resolved identity set for a user."""
    user_id: str
    primary_email: str
    emails: Set[str] = field(default_factory=set)
    phones: Set[str] = field(default_factory=set)
    names: Set[str] = field(default_factory=set)
    email_hashes: Set[str] = field(default_factory=set)
    tombstone_ids: Set[str] = field(default_factory=set)
    account_id: Optional[str] = None
    audit_record_id: Optional[str] = None
    associated_resources: Set[str] = field(default_factory=set)

    def matches_email(self, email: str) -> bool:
        """Checks if a given email belongs to this subject (case-insensitive)."""
        return email.strip().lower() in self.emails

    def matches_hash(self, email_hash: str) -> bool:
        """Checks if a given SHA-256 hash matches any of subject's emails."""
        return email_hash.strip().lower() in self.email_hashes

    def matches_phone(self, phone: str) -> bool:
        """Checks if a given phone number belongs to this subject."""
        normalized = phone.strip()
        return normalized in self.phones


class IdentityResolver:
    """Builds an in-memory identity graph from user_identities, user_audit_log, and system_activity."""

    def __init__(
        self,
        identities_path: str = "dataset/user_identities.csv",
        audit_log_path: str = "dataset/user_audit_log.csv",
        activity_path: str = "dataset/system_activity.csv",
    ):
        self.identities_path = Path(identities_path)
        self.audit_log_path = Path(audit_log_path)
        self.activity_path = Path(activity_path)

        # Mapping: user_id -> dict of profile fields
        self.users_by_id: Dict[str, Dict[str, str]] = {}
        # Mapping: lowercase email -> user_id
        self.email_to_user_id: Dict[str, str] = {}
        # Mapping: user_id -> set of historical emails
        self.historical_emails_by_user_id: Dict[str, Set[str]] = {}
        # Mapping: user_id -> set of historical phones
        self.historical_phones_by_user_id: Dict[str, Set[str]] = {}
        # Mapping: user_id -> set of historical names
        self.historical_names_by_user_id: Dict[str, Set[str]] = {}
        # Mapping: user_id -> set of tombstone resource IDs
        self.tombstones_by_user_id: Dict[str, Set[str]] = {}
        # Mapping: email/user_id -> account_id
        self.email_to_account: Dict[str, str] = {}
        self.user_to_account: Dict[str, str] = {}
        # Mapping: user_id -> audit_record_id
        self.user_to_audit_record: Dict[str, str] = {}
        # Mapping: user_id -> associated resources
        self.associated_resources_by_user: Dict[str, Set[str]] = {}

        self._load_data()

    def _load_data(self) -> None:
        """Loads and indexes identity datasets."""
        self._load_identities()
        self._load_audit_log()
        self._load_evidence_linkages()

    def _load_identities(self) -> None:
        """Parses user_identities.csv snapshot."""
        if not self.identities_path.exists():
            return

        with open(self.identities_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                user_id = row["user_id"].strip()
                email = row["email"].strip().lower()
                self.users_by_id[user_id] = {
                    "name": row["name"].strip(),
                    "email": email,
                    "phone": row["phone"].strip(),
                    "email_hash": row["email_hash"].strip().lower(),
                }
                self.email_to_user_id[email] = user_id

    def _load_audit_log(self) -> None:
        """Parses user_audit_log.csv for historical identifier mutations."""
        if not self.audit_log_path.exists():
            return

        with open(self.audit_log_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                user_id = row["user_id"].strip()
                field_name = row["field_name"].strip()
                old_val = row["old_value"].strip()
                new_val = row["new_value"].strip()

                if field_name == "email":
                    self.historical_emails_by_user_id.setdefault(user_id, set()).update([old_val.lower(), new_val.lower()])
                    # Map old and new historical emails to user_id
                    self.email_to_user_id[old_val.lower()] = user_id
                    self.email_to_user_id[new_val.lower()] = user_id
                elif field_name == "phone":
                    self.historical_phones_by_user_id.setdefault(user_id, set()).update([old_val, new_val])
                elif field_name == "name":
                    self.historical_names_by_user_id.setdefault(user_id, set()).update([old_val, new_val])

    def _load_evidence_linkages(self) -> None:
        """Loads account IDs, audit record IDs, and resource associations across evidence and activity."""
        dataset_dir = self.identities_path.parent

        # 1. Handover text (customer_account_handover_20261001.txt)
        p_handover = dataset_dir / "evidence" / "records" / "customer_account_handover_20261001.txt"
        if p_handover.exists():
            with open(p_handover, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "|" in line and "account_service" in line:
                        parts = [x.strip() for x in line.split("|")]
                        if len(parts) >= 6:
                            rid = parts[2]
                            ident = parts[5].lower()
                            self.email_to_account[ident] = rid
                            if ident in self.email_to_user_id:
                                uid = self.email_to_user_id[ident]
                                self.user_to_account[uid] = rid

        # 2. Snapshot bundles
        records_dir = dataset_dir / "evidence" / "records"
        if records_dir.exists():
            for p in records_dir.glob("customer_data_snapshot_bundle_*.json"):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    for s in data.get("snapshots", []):
                        store = s.get("data_store")
                        for r in s.get("records", []):
                            rid = r.get("resource_id")
                            cref = r.get("customer_reference") or r.get("subject_reference")
                            em = r.get("email")
                            if store == "account_service" and rid:
                                if cref:
                                    self.user_to_account[cref] = rid
                                if em:
                                    self.email_to_account[em.lower()] = rid
                            elif store == "security_service" and rid:
                                if cref:
                                    self.user_to_audit_record[cref] = rid
                except Exception:
                    pass

        # 3. Log trace pairing
        logs_dir = dataset_dir / "evidence" / "logs"
        if logs_dir.exists():
            import re
            for p in logs_dir.glob("*.log"):
                traces: Dict[str, Dict[str, str]] = {}
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            m_tid = re.search(r'["\']?(?:trace_id|requestId)["\']?[:=]\s*["\']?([a-zA-Z0-9_\-]+)', line)
                            m_acc = re.search(r'\b(account_\d+)\b', line)
                            m_usr = re.search(r'\b(user_\d+)\b', line)
                            m_em = re.search(r'[\w\.-]+@[\w\.-]+', line)
                            m_aud = re.search(r'\b(audit_record_\d+)\b', line)
                            if m_tid:
                                tid = m_tid.group(1)
                                if tid not in traces:
                                    traces[tid] = {}
                                if m_acc:
                                    traces[tid]["acc"] = m_acc.group(1)
                                if m_usr:
                                    traces[tid]["usr"] = m_usr.group(1)
                                if m_em:
                                    traces[tid]["em"] = m_em.group(0).lower()
                                if m_aud:
                                    traces[tid]["aud"] = m_aud.group(1)
                    for tid, ctx in traces.items():
                        acc = ctx.get("acc")
                        usr = ctx.get("usr")
                        em = ctx.get("em")
                        aud = ctx.get("aud")
                        if acc:
                            if em:
                                self.email_to_account[em] = acc
                            if usr:
                                self.user_to_account[usr] = acc
                        if aud and usr:
                            self.user_to_audit_record[usr] = aud
                except Exception:
                    pass

        # 4. Activity linkages
        if self.activity_path.exists():
            with open(self.activity_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tgt = row.get("target_system", "")
                    res_id = row.get("resource_id", "")
                    details = row.get("details", "")
                    # Tombstones
                    if tgt == "identity_service" and res_id.startswith("tombstone_"):
                        for user_id in self.users_by_id.keys():
                            if user_id in details:
                                self.tombstones_by_user_id.setdefault(user_id, set()).add(res_id)
                    # Associated resources mentioned with user_id
                    for user_id in self.users_by_id.keys():
                        if user_id in details and res_id:
                            self.associated_resources_by_user.setdefault(user_id, set()).add(res_id)

    def resolve(self, email: str) -> Optional[SubjectIdentity]:
        """Resolves full current and historical identity graph given an email address."""
        normalized_email = email.strip().lower()
        user_id = self.email_to_user_id.get(normalized_email)
        if not user_id:
            return None

        profile = self.users_by_id.get(user_id, {})
        primary_email = profile.get("email", normalized_email)

        # Collect all email addresses
        emails = {primary_email, normalized_email}
        if user_id in self.historical_emails_by_user_id:
            emails.update(self.historical_emails_by_user_id[user_id])

        # Collect all phone numbers
        phones = set()
        if "phone" in profile and profile["phone"]:
            phones.add(profile["phone"])
        if user_id in self.historical_phones_by_user_id:
            phones.update(self.historical_phones_by_user_id[user_id])

        # Collect all names
        names = set()
        if "name" in profile and profile["name"]:
            names.add(profile["name"])
        if user_id in self.historical_names_by_user_id:
            names.update(self.historical_names_by_user_id[user_id])

        # Collect/generate all email hashes
        email_hashes = set()
        if "email_hash" in profile and profile["email_hash"]:
            email_hashes.add(profile["email_hash"])
        for em in emails:
            h = hashlib.sha256(em.strip().lower().encode("utf-8")).hexdigest()
            email_hashes.add(h)

        # Collect tombstones
        tombstones = set()
        if user_id in self.tombstones_by_user_id:
            tombstones.update(self.tombstones_by_user_id[user_id])

        # Resolve account_id
        account_id = None
        if user_id.startswith("user_"):
            try:
                num = int(user_id.split("_")[1])
                if num <= 10:
                    account_id = f"account_{num:03d}"
            except ValueError:
                pass
        if not account_id:
            account_id = (
                self.email_to_account.get(normalized_email)
                or self.email_to_account.get(primary_email)
                or self.user_to_account.get(user_id)
            )

        # Resolve audit_record_id
        audit_record_id = self.user_to_audit_record.get(user_id)

        # Associated resources
        assoc = set()
        if user_id in self.associated_resources_by_user:
            assoc.update(self.associated_resources_by_user[user_id])
        if account_id:
            assoc.add(account_id)
        if audit_record_id:
            assoc.add(audit_record_id)

        return SubjectIdentity(
            user_id=user_id,
            primary_email=primary_email,
            emails=emails,
            phones=phones,
            names=names,
            email_hashes=email_hashes,
            tombstone_ids=tombstones,
            account_id=account_id,
            audit_record_id=audit_record_id,
            associated_resources=assoc,
        )
