"""Deletion Audit Policy & Deterministic Step Sequencing Engine.

Applies deletion_rules.csv to observed system resources, determines
deletion_status (COMPLETE, INCOMPLETE, NOT_APPLICABLE), and generates
strictly ordered, evidence-backed step arrays.
"""

from typing import Any, Dict, List, Tuple, Optional
from code.evidence_scanner import ObservedResource


# Exact operation ordering weights per problem_statement.md & AGENTS.md §6.4
OPERATION_ORDER: Dict[str, int] = {
    # Phase: FINDING
    "REPORT_REMAINING_RECORD": 1,
    "REPORT_EXPOSED_PII": 2,
    "REPORT_ACTIVE_DATA_FLOW": 3,
    "REPORT_RESTORE_RISK": 4,

    # Phase: REMEDIATION
    "DISABLE_DATA_FLOW": 10,
    "BLOCK_RESTORE": 11,
    "DELETE_RECORD": 12,
    "REDACT_RECORD": 13,
    "ANONYMIZE_RECORD": 14,
    
    # Phase: VERIFICATION
    "VERIFY_RECORD_ABSENT": 20,
    "VERIFY_RECORD_PRESENT": 21,
    "VERIFY_RECORD_REDACTED": 22,
    "VERIFY_RECORD_ANONYMIZED": 23,
    "VERIFY_DATA_FLOW_DISABLED": 24,
    "VERIFY_RESTORE_BLOCKED": 25,
}

PHASE_ORDER: Dict[str, int] = {
    "FINDING": 1,
    "REMEDIATION": 2,
    "VERIFICATION": 3,
}


class DeletionAuditor:
    """Evaluates observed resources against deletion policy and generates step objects."""

    def audit_case(
        self,
        case_id: str,
        is_deletion_authorized: bool,
        observed_resources: List[ObservedResource],
        identity: Optional[Any] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Audits a single case and returns (deletion_status, steps_list)."""
        # Filter 1: If request does not authorize deletion, return NOT_APPLICABLE with []
        if not is_deletion_authorized:
            return "NOT_APPLICABLE", []

        findings: List[Dict[str, Any]] = []
        remediations: List[Dict[str, Any]] = []
        verifications: List[Dict[str, Any]] = []

        # Determine non-compliant resources
        violations = [r for r in observed_resources if not r.is_compliant]

        if not violations:
            # Case is COMPLETE: Emit evidence-backed verification steps only
            for res in observed_resources:
                step = self._build_complete_verification_step(res)
                if step:
                    verifications.append(step)

            sorted_steps = self._sort_and_number_steps(verifications)
            return "COMPLETE", sorted_steps
        else:
            # Case is INCOMPLETE: Emit Findings, Remediation Plan, and Future Verification
            for res in observed_resources:
                if not res.is_compliant:
                    f_step = self._build_finding_step(res)
                    r_step = self._build_remediation_step(res)
                    v_step = self._build_future_verification_step(res)
                    if f_step:
                        findings.append(f_step)
                    if r_step:
                        remediations.append(r_step)
                    if v_step:
                        verifications.append(v_step)
                else:
                    # Policy-required retained records (e.g. security audit log) or absent accounts
                    v_step = self._build_future_verification_step(res)
                    if v_step:
                        verifications.append(v_step)

            # Ensure account_service and security_service verification steps exist for INCOMPLETE cases if known
            if identity:
                has_account_v = any(v.get("system_id") == "account_service" for v in verifications)
                if not has_account_v and getattr(identity, "account_id", None):
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": "account_service",
                        "resource_id": identity.account_id,
                        "operation": "VERIFY_RECORD_ABSENT",
                        "state": "ABSENT",
                        "evidence_id": "",
                    })

                has_security_v = any(v.get("system_id") == "security_service" for v in verifications)
                if not has_security_v and getattr(identity, "audit_record_id", None):
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": "security_service",
                        "resource_id": identity.audit_record_id,
                        "operation": "VERIFY_RECORD_PRESENT",
                        "state": "PRESENT",
                        "evidence_id": "",
                    })

            all_steps = findings + remediations + verifications
            sorted_steps = self._sort_and_number_steps(all_steps)
            return "INCOMPLETE", sorted_steps

    def _build_finding_step(self, res: ObservedResource) -> Optional[Dict[str, Any]]:
        """Constructs a FINDING step citing the proving evidence."""
        op = None
        state = res.state

        if (
            res.system_id in ("account_service", "search_service", "export_service")
            or (res.system_id == "support_platform" and res.data_category == "SUPPORT_ATTACHMENT")
            or (res.system_id == "analytics_platform" and res.data_category in ("MARKETING_PROFILE", "SUPPORT_ATTACHMENT"))
        ):
            op = "REPORT_REMAINING_RECORD"
            state = "PRESENT"
        elif res.system_id in ("support_platform", "analytics_platform", "identity_service"):
            op = "REPORT_EXPOSED_PII"
            state = "PRESENT"
        elif res.system_id == "integration_service":
            op = "REPORT_ACTIVE_DATA_FLOW"
            state = "ACTIVE"
        elif res.system_id == "backup_service":
            op = "REPORT_RESTORE_RISK"
            state = "ACTIVE"

        if not op:
            return None

        return {
            "phase": "FINDING",
            "system_id": res.system_id,
            "resource_id": res.resource_id,
            "operation": op,
            "state": state,
            "evidence_id": res.evidence_id,
        }

    def _build_remediation_step(self, res: ObservedResource) -> Optional[Dict[str, Any]]:
        """Constructs a prospective REMEDIATION step with evidence_id = ''."""
        op = None
        state = None

        if res.system_id == "integration_service":
            op = "DISABLE_DATA_FLOW"
            state = "DISABLED"
        elif res.system_id == "backup_service":
            op = "BLOCK_RESTORE"
            state = "BLOCKED"
        elif (
            res.system_id in ("account_service", "search_service", "export_service")
            or (res.system_id == "support_platform" and res.data_category == "SUPPORT_ATTACHMENT")
            or (res.system_id == "analytics_platform" and res.data_category in ("MARKETING_PROFILE", "SUPPORT_ATTACHMENT"))
        ):
            op = "DELETE_RECORD"
            state = "ABSENT"
        elif res.system_id in ("support_platform", "identity_service"):
            op = "REDACT_RECORD"
            state = "REDACTED"
        elif res.system_id == "analytics_platform":
            op = "ANONYMIZE_RECORD"
            state = "ANONYMIZED"

        if not op or not state:
            return None

        return {
            "phase": "REMEDIATION",
            "system_id": res.system_id,
            "resource_id": res.resource_id,
            "operation": op,
            "state": state,
            "evidence_id": "",
        }

    def _build_future_verification_step(self, res: ObservedResource) -> Optional[Dict[str, Any]]:
        """Constructs a prospective post-remediation VERIFICATION step with evidence_id = ''."""
        op = None
        state = None

        if (
            res.system_id in ("account_service", "search_service", "export_service")
            or (res.system_id == "support_platform" and res.data_category == "SUPPORT_ATTACHMENT")
            or (res.system_id == "analytics_platform" and res.data_category in ("MARKETING_PROFILE", "SUPPORT_ATTACHMENT"))
        ):
            op = "VERIFY_RECORD_ABSENT"
            state = "ABSENT"
        elif res.system_id == "security_service":
            op = "VERIFY_RECORD_PRESENT"
            state = "PRESENT"
        elif res.system_id in ("support_platform", "identity_service"):
            op = "VERIFY_RECORD_REDACTED"
            state = "REDACTED"
        elif res.system_id == "analytics_platform":
            op = "VERIFY_RECORD_ANONYMIZED"
            state = "ANONYMIZED"
        elif res.system_id == "integration_service":
            op = "VERIFY_DATA_FLOW_DISABLED"
            state = "DISABLED"
        elif res.system_id == "backup_service":
            op = "VERIFY_RESTORE_BLOCKED"
            state = "BLOCKED"

        if not op or not state:
            return None

        return {
            "phase": "VERIFICATION",
            "system_id": res.system_id,
            "resource_id": res.resource_id,
            "operation": op,
            "state": state,
            "evidence_id": "",
        }

    def _build_complete_verification_step(self, res: ObservedResource) -> Optional[Dict[str, Any]]:
        """Constructs an evidence-backed VERIFICATION step for a COMPLETE case."""
        op = None
        state = res.state

        if (
            res.system_id in ("account_service", "search_service", "export_service")
            or (res.system_id == "support_platform" and res.data_category == "SUPPORT_ATTACHMENT")
            or (res.system_id == "analytics_platform" and res.data_category in ("MARKETING_PROFILE", "SUPPORT_ATTACHMENT"))
        ):
            op = "VERIFY_RECORD_ABSENT"
            state = "ABSENT"
        elif res.system_id == "security_service":
            op = "VERIFY_RECORD_PRESENT"
            state = "PRESENT"
        elif res.system_id in ("support_platform", "identity_service"):
            op = "VERIFY_RECORD_REDACTED"
            state = "REDACTED"
        elif res.system_id == "analytics_platform":
            op = "VERIFY_RECORD_ANONYMIZED"
            state = "ANONYMIZED"
        elif res.system_id == "integration_service":
            op = "VERIFY_DATA_FLOW_DISABLED"
            state = "DISABLED"
        elif res.system_id == "backup_service":
            op = "VERIFY_RESTORE_BLOCKED"
            state = "BLOCKED"

        if not op:
            return None

        return {
            "phase": "VERIFICATION",
            "system_id": res.system_id,
            "resource_id": res.resource_id,
            "operation": op,
            "state": state,
            "evidence_id": res.evidence_id,
        }

    def _sort_and_number_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sorts steps by phase -> operation order -> system_id ASC -> resource_id ASC."""
        def sort_key(s: Dict[str, Any]):
            p_weight = PHASE_ORDER.get(s["phase"], 99)
            op_weight = OPERATION_ORDER.get(s["operation"], 99)
            sys_id = s.get("system_id", "")
            res_id = s.get("resource_id", "")
            return (p_weight, op_weight, sys_id, res_id)

        sorted_list = sorted(steps, key=sort_key)

        # Number consecutively from 1
        for idx, step in enumerate(sorted_list, start=1):
            step["step_no"] = idx

        return sorted_list
