"""Unit tests for the Deletion Policy & Step Sequencer Engine (code/auditor.py).

Verifies NOT_APPLICABLE handling, COMPLETE verification step generation,
INCOMPLETE finding/remediation/verification generation, phase and operation ordering,
and evidence citation contracts.
"""

import unittest
from code.auditor import DeletionAuditor
from code.evidence_scanner import ObservedResource


class TestDeletionAuditor(unittest.TestCase):
    """Test suite for DeletionAuditor."""

    def setUp(self):
        self.auditor = DeletionAuditor()

    def test_non_deletion_returns_not_applicable(self):
        """Test that unauthorized deletion requests return NOT_APPLICABLE with empty array."""
        status, steps = self.auditor.audit_case(
            case_id="case_538",
            is_deletion_authorized=False,
            observed_resources=[],
        )
        self.assertEqual(status, "NOT_APPLICABLE")
        self.assertEqual(steps, [])

    def test_clean_state_returns_complete_with_evidence_citations(self):
        """Test clean deletion case emitting only evidence-backed verification steps."""
        resources = [
            ObservedResource(
                system_id="account_service",
                resource_id="account_001",
                state="ABSENT",
                evidence_id="evidence_54",
                is_compliant=True,
            )
        ]
        status, steps = self.auditor.audit_case("case_01", True, resources)
        self.assertEqual(status, "COMPLETE")
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["step_no"], 1)
        self.assertEqual(steps[0]["phase"], "VERIFICATION")
        self.assertEqual(steps[0]["operation"], "VERIFY_RECORD_ABSENT")
        self.assertEqual(steps[0]["evidence_id"], "evidence_54")

    def test_violation_returns_incomplete_with_ordered_triad(self):
        """Test remaining record emitting Finding, Remediation, and Verification."""
        resources = [
            ObservedResource(
                system_id="account_service",
                resource_id="account_005",
                state="PRESENT",
                evidence_id="evidence_54",
                is_compliant=False,
            )
        ]
        status, steps = self.auditor.audit_case("case_05", True, resources)
        self.assertEqual(status, "INCOMPLETE")
        self.assertEqual(len(steps), 3)

        # 1. Finding
        self.assertEqual(steps[0]["step_no"], 1)
        self.assertEqual(steps[0]["phase"], "FINDING")
        self.assertEqual(steps[0]["operation"], "REPORT_REMAINING_RECORD")
        self.assertEqual(steps[0]["evidence_id"], "evidence_54")

        # 2. Remediation
        self.assertEqual(steps[1]["step_no"], 2)
        self.assertEqual(steps[1]["phase"], "REMEDIATION")
        self.assertEqual(steps[1]["operation"], "DELETE_RECORD")
        self.assertEqual(steps[1]["evidence_id"], "")

        # 3. Verification
        self.assertEqual(steps[2]["step_no"], 3)
        self.assertEqual(steps[2]["phase"], "VERIFICATION")
        self.assertEqual(steps[2]["operation"], "VERIFY_RECORD_ABSENT")
        self.assertEqual(steps[2]["evidence_id"], "")

    def test_remediation_dependency_ordering(self):
        """Test that data flows are disabled before record deletes in remediation."""
        resources = [
            ObservedResource(
                system_id="search_service",
                resource_id="search_052",
                state="PRESENT",
                evidence_id="evidence_03",
                is_compliant=False,
            ),
            ObservedResource(
                system_id="integration_service",
                resource_id="data_flow_9522",
                state="ACTIVE",
                evidence_id="evidence_03",
                is_compliant=False,
            ),
        ]
        status, steps = self.auditor.audit_case("case_11", True, resources)
        self.assertEqual(status, "INCOMPLETE")

        # Filter remediation steps
        rem_steps = [s for s in steps if s["phase"] == "REMEDIATION"]
        self.assertEqual(len(rem_steps), 2)
        # DISABLE_DATA_FLOW must come before DELETE_RECORD
        self.assertEqual(rem_steps[0]["operation"], "DISABLE_DATA_FLOW")
        self.assertEqual(rem_steps[1]["operation"], "DELETE_RECORD")


if __name__ == "__main__":
    unittest.main()
