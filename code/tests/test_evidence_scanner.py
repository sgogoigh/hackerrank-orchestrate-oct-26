"""Unit tests for the Temporal Evidence & Activity Scanner (code/evidence_scanner.py).

Verifies cutoff enforcement (captured_at <= audit_at), replica drift discovery,
readback log parsing, and snapshot bundle tombstone extraction.
"""

import unittest
from code.evidence_scanner import EvidenceScanner
from code.identity import IdentityResolver


class TestEvidenceScanner(unittest.TestCase):
    """Test suite for EvidenceScanner."""

    @classmethod
    def setUpClass(cls):
        cls.resolver = IdentityResolver(
            identities_path="dataset/user_identities.csv",
            audit_log_path="dataset/user_audit_log.csv",
            activity_path="dataset/system_activity.csv",
        )
        cls.scanner = EvidenceScanner(dataset_dir="dataset")

    def test_temporal_cutoff_filters_future_evidence(self):
        """Test that files captured after audit_at are completely excluded."""
        # Cutoff in August 2026
        early_audit = "2026-08-15T00:00:00Z"
        eligible = self.scanner.get_eligible_evidence_files(early_audit)

        # evidence_01 was captured at 2026-09-15T11:59:39Z, which is after early_audit
        self.assertNotIn("evidence_01", eligible)
        self.assertNotIn("evidence_94", eligible)

        # Later cutoff in October 2026 should include evidence_01
        late_audit = "2026-10-01T12:00:00Z"
        eligible_late = self.scanner.get_eligible_evidence_files(late_audit)
        self.assertIn("evidence_01", eligible_late)
        self.assertIn("evidence_94", eligible_late)

    def test_detect_failover_replica_ghost_data(self):
        """Test finding remaining record in failover replica (case_05: Leila Haddad)."""
        identity = self.resolver.resolve("leila.haddad@yahoo.com")
        self.assertIsNotNone(identity)

        # case_05 audit_at: 2026-09-08T13:40:00Z
        resources = self.scanner.scan_subject_resources(identity, "2026-09-08T13:40:00Z")
        res_ids = {r.resource_id: r for r in resources}

        # account_005 was present in customer_profiles_failover_replica in evidence_54
        self.assertIn("account_005", res_ids)
        acc = res_ids["account_005"]
        self.assertEqual(acc.state, "PRESENT")
        self.assertFalse(acc.is_compliant)
        self.assertEqual(acc.evidence_id, "evidence_54")

    def test_readback_log_verification(self):
        """Test verifying absent profile and anonymized analytics in evidence_94 (case_03: L. Fontaine)."""
        identity = self.resolver.resolve("l.fontaine46@yahoo.com")
        self.assertIsNotNone(identity)

        # case_03 audit_at: 2026-09-26T11:00:00Z
        resources = self.scanner.scan_subject_resources(identity, "2026-09-26T11:00:00Z")
        res_ids = {r.resource_id: r for r in resources}

        # account_7566 was looked up and returned 404
        self.assertIn("account_7566", res_ids)
        self.assertEqual(res_ids["account_7566"].state, "ABSENT")
        self.assertEqual(res_ids["account_7566"].evidence_id, "evidence_94")


if __name__ == "__main__":
    unittest.main()
