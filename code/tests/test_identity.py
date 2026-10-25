"""Unit tests for the Subject Identity Resolution Module (code/identity.py).

Tests direct primary email matches, historical email alias resolution,
phone/name tracking, email hash generation, and case normalization.
"""

import unittest
from code.identity import IdentityResolver, SubjectIdentity


class TestIdentityResolver(unittest.TestCase):
    """Test suite for IdentityResolver against dataset records."""

    @classmethod
    def setUpClass(cls):
        cls.resolver = IdentityResolver(
            identities_path="dataset/user_identities.csv",
            audit_log_path="dataset/user_audit_log.csv",
            activity_path="dataset/system_activity.csv",
        )

    def test_direct_primary_email_match(self):
        """Test resolving an identity present directly in user_identities.csv."""
        # Amina El-Masri (user_01)
        identity = self.resolver.resolve("amina.elmasri@gmail.com")
        self.assertIsNotNone(identity)
        self.assertEqual(identity.user_id, "user_01")
        self.assertEqual(identity.primary_email, "amina.elmasri@gmail.com")
        self.assertIn("Amina El-Masri", identity.names)
        self.assertTrue(identity.matches_email("amina.elmasri@gmail.com"))
        self.assertTrue(identity.matches_email("AMINA.ELMASRI@GMAIL.COM"))

    def test_historical_email_alias_resolution(self):
        """Test resolving a user who submitted a request using an obsolete historical email."""
        # Nadia Ionescu / Nadia Petrescu (user_10, case_10)
        # Old email: nadia.ionescu@yahoo.com, New email: n.petrescu@yahoo.com
        identity = self.resolver.resolve("nadia.ionescu@yahoo.com")
        self.assertIsNotNone(identity)
        self.assertEqual(identity.user_id, "user_10")
        # Should include both old and new addresses in the identity email set
        self.assertIn("nadia.ionescu@yahoo.com", identity.emails)
        self.assertIn("n.petrescu@yahoo.com", identity.emails)

    def test_case_insensitivity_and_normalization(self):
        """Test that uppercase and mixed-case emails resolve correctly."""
        # Sipho Mokoena (case_38: SIPHO.MOKOENA@GMAIL.COM)
        identity_upper = self.resolver.resolve("SIPHO.MOKOENA@GMAIL.COM")
        identity_lower = self.resolver.resolve("sipho.mokoena@gmail.com")
        self.assertIsNotNone(identity_upper)
        self.assertIsNotNone(identity_lower)
        self.assertEqual(identity_upper.user_id, identity_lower.user_id)

    def test_email_hash_generation(self):
        """Test that SHA-256 hashes are accurately generated for all aliases."""
        identity = self.resolver.resolve("amina.elmasri@gmail.com")
        self.assertIsNotNone(identity)
        # d4e1f59abcf9a1e0cfdc7c27ad6c07ed4ff88b326a16ed5eed5ec6bc31618c93
        self.assertIn("d4e1f59abcf9a1e0cfdc7c27ad6c07ed4ff88b326a16ed5eed5ec6bc31618c93", identity.email_hashes)

    def test_unknown_email_returns_none(self):
        """Test that a non-existent email returns None."""
        identity = self.resolver.resolve("non_existent_user_999999@domain.com")
        self.assertNone(identity)


if __name__ == "__main__":
    unittest.main()
