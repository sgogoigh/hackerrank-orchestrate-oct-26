"""Unit tests for the Multilingual Request Intent Classification Module (code/classifier.py).

Verifies accurate detection of non-deletion requests (marketing opt-out, access, export)
and valid multilingual deletion authorizations (English, Spanish, French, Japanese, Korean, Portuguese).
"""

import tempfile
import unittest
from pathlib import Path
from code.classifier import IntentClassifier


class TestIntentClassifier(unittest.TestCase):
    """Test suite for IntentClassifier."""

    def setUp(self):
        # Use a temporary cache file to avoid mutating shared cache during unit tests
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = Path(self.temp_dir.name) / "test_intent_cache.json"
        self.classifier = IntentClassifier(cache_path=str(self.cache_path))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_marketing_opt_out_classified_as_non_deletion(self):
        """Test case_538: User explicitly requests marketing opt-out only."""
        text = "Please remove me from marketing lists only. I still want receipts and service messages for this account."
        is_del, intent = self.classifier.classify("case_538", text)
        self.assertFalse(is_del)
        self.assertEqual(intent, "MARKETING_OPT_OUT")

    def test_rectification_phone_update_non_deletion(self):
        """Test case_533: User requests phone update leaving account active."""
        text = "The mobile number on my profile is out of date. Please replace it with the new one and leave the account active."
        is_del, intent = self.classifier.classify("case_533", text)
        self.assertFalse(is_del)
        self.assertEqual(intent, "RECTIFICATION")

    def test_data_access_sar_non_deletion(self):
        """Test case_539: User requests data disclosure without deletion."""
        text = "Can you tell me what personal information you hold about me? This is an information request, not a request to erase it."
        is_del, intent = self.classifier.classify("case_539", text)
        self.assertFalse(is_del)
        self.assertEqual(intent, "DATA_ACCESS")

    def test_support_account_reset_do_not_close(self):
        """Test case_536: User requests login reset stating do not close account."""
        text = "I can't access my profile and need help resetting the login. Do not close the account."
        is_del, intent = self.classifier.classify("case_536", text)
        self.assertFalse(is_del)
        self.assertEqual(intent, "ACCOUNT_SUPPORT")

    def test_data_export_non_deletion(self):
        """Test case_535: User requests portable download keeping account."""
        text = "I'd like to download my account information in a portable format. Please keep the account as it is."
        is_del, intent = self.classifier.classify("case_535", text)
        self.assertFalse(is_del)
        self.assertEqual(intent, "DATA_EXPORT")

    def test_english_deletion_request(self):
        """Test case_01: Standard English deletion directive."""
        text = "Hi, I haven’t used this account in years and would like it closed. Please remove the profile and the personal details attached to it."
        is_del, intent = self.classifier.classify("case_01", text)
        self.assertTrue(is_del)
        self.assertEqual(intent, "DELETION")

    def test_spanish_deletion_request(self):
        """Test case_02: Spanish deletion authorization."""
        text = "Intenté eliminar mi cuenta ayer, pero la página terminó mostrando un error. ¿Pueden comprobar si todavía queda algún dato y completar la eliminación si hace falta?"
        is_del, intent = self.classifier.classify("case_02", text)
        self.assertTrue(is_del)
        self.assertEqual(intent, "DELETION")

    def test_french_deletion_request(self):
        """Test case_03: French deletion authorization."""
        text = "Je demande la suppression définitive du compte associé à cette adresse e-mail. Veuillez examiner les identifiants actuels et antérieurs conformément à votre procédure de confidentialité."
        is_del, intent = self.classifier.classify("case_03", text)
        self.assertTrue(is_del)
        self.assertEqual(intent, "DELETION")

    def test_japanese_deletion_request(self):
        """Test case_14: Japanese deletion authorization."""
        text = "このメールアドレスに関連するアカウントの完全な削除を依頼します。 プライバシー手続きに従い、現在および過去の識別情報を確認してください。"
        is_del, intent = self.classifier.classify("case_14", text)
        self.assertTrue(is_del)
        self.assertEqual(intent, "DELETION")

    def test_korean_deletion_request(self):
        """Test case_66: Korean deletion authorization."""
        text = "이 이메일 주소에 연결된 계정의 영구 삭제를 요청합니다. 개인정보 처리 절차에 따라 현재 및 이전 식별자를 검토해 주세요."
        is_del, intent = self.classifier.classify("case_66", text)
        self.assertTrue(is_del)
        self.assertEqual(intent, "DELETION")

    def test_portuguese_deletion_request(self):
        """Test case_54: Portuguese deletion authorization."""
        text = "Solicito a exclusão permanente da conta associada a este e-mail. Verifiquem os identificadores atuais e anteriores conforme o processo de privacidade."
        is_del, intent = self.classifier.classify("case_54", text)
        self.assertTrue(is_del)
        self.assertEqual(intent, "DELETION")

    def test_caching_behavior(self):
        """Test that subsequent calls hit the local cache without re-evaluation."""
        case_id = "test_cache_case"
        text = "Permanently close and delete my account."
        is_del1, _ = self.classifier.classify(case_id, text)
        self.assertTrue(is_del1)

        # Mutate the cache entry to verify readback
        self.classifier.cache[case_id]["intent"] = "CACHED_RESULT"
        _, intent2 = self.classifier.classify(case_id, text)
        self.assertEqual(intent2, "CACHED_RESULT")


if __name__ == "__main__":
    unittest.main()
