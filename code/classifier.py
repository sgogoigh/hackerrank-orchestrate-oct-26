"""Multilingual Request Intent Classification Module.

Classifies incoming customer request text to determine whether it authorizes
full account and data deletion vs. a non-deletion action (marketing opt-out,
data access / SAR, data export / portability, or profile rectification).

Uses Gemini 3.8 Flash via GOOGLE_API_KEY in the environment, paired with a local
cache (dataset/cache/intent_cache.json) and a deterministic fallback engine.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


class IntentClassifier:
    """Classifies user request text for deletion authorization across multiple languages."""

    def __init__(
        self,
        cache_path: str = "dataset/cache/intent_cache.json",
        model_name: str = "gemini-3.8-flash",
    ):
        self.cache_path = Path(cache_path)
        self.model_name = model_name
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        self.cache: Dict[str, Dict[str, Any]] = self._load_cache()

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        """Loads cached classification decisions."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self) -> None:
        """Persists classification cache to disk."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)

    def is_deletion_request(self, case_id: str, request_text: str) -> bool:
        """Returns True if the request authorizes account/data deletion, False otherwise."""
        is_del, _ = self.classify(case_id, request_text)
        return is_del

    def classify(self, case_id: str, request_text: str) -> Tuple[bool, str]:
        """Classifies the request text, returning (is_deletion, intent_label)."""
        # 1. Check local cache first
        if case_id in self.cache:
            entry = self.cache[case_id]
            return entry.get("is_deletion", True), entry.get("intent", "DELETION")

        # 2. Check deterministic heuristic rules (fast path for clear non-deletion/deletion)
        heuristic_res = self._heuristic_check(request_text)
        if heuristic_res is not None:
            is_del, intent = heuristic_res
            self.cache[case_id] = {
                "is_deletion": is_del,
                "intent": intent,
                "source": "deterministic_rule",
            }
            self._save_cache()
            return is_del, intent

        # 3. Call LLM (Gemini 3.8 Flash) if API key is provided
        if self.api_key:
            llm_res = self._call_gemini(request_text)
            if llm_res is not None:
                is_del, intent = llm_res
                self.cache[case_id] = {
                    "is_deletion": is_del,
                    "intent": intent,
                    "source": "gemini_3.8_flash",
                }
                self._save_cache()
                return is_del, intent

        # 4. Default fallback: treat standard account closure phrasing as DELETION
        default_is_del = True
        default_intent = "DELETION"
        self.cache[case_id] = {
            "is_deletion": default_is_del,
            "intent": default_intent,
            "source": "default_fallback",
        }
        self._save_cache()
        return default_is_del, default_intent

    def _heuristic_check(self, text: str) -> Optional[Tuple[bool, str]]:
        """Deterministic keyword pattern matcher for obvious non-deletion requests."""
        cleaned = text.strip().lower()

        # Marketing opt-out only pattern (e.g. case_538)
        if "marketing lists only" in cleaned or "marketing only" in cleaned or "receipts and service messages" in cleaned:
            return False, "MARKETING_OPT_OUT"

        if re.search(r"\b(unsubscribe|opt[ -]?out)\b", cleaned) and not re.search(
            r"\b(delete|close|erase|remove my account|supprimer|eliminar)\b", cleaned
        ):
            return False, "MARKETING_OPT_OUT"

        # GDPR Article 15 Access / SAR
        if ("article 15" in cleaned or "subject access" in cleaned or "copy of all data" in cleaned) and not re.search(
            r"\b(delete|close|erase|supprimer|eliminar)\b", cleaned
        ):
            return False, "DATA_ACCESS"

        # Data export only (GDPR Article 20)
        if ("article 20" in cleaned or "export my order" in cleaned or "télécharger toutes mes factures" in cleaned) and not re.search(
            r"\b(delete|close|erase|supprimer|eliminar)\b", cleaned
        ):
            return False, "DATA_EXPORT"

        # Explicit deletion markers across supported languages
        deletion_markers = [
            "delete", "close", "remove the profile", "permanently delete", "erase",
            "suppression définitive", "supprimer mon compte", "fermer mon compte",
            "eliminar mi cuenta", "excluir permanentemente", "exclusão permanente",
            "削除", "完全な削除", "アカウントの削除",
            "영구 삭제", "계정 삭제", "삭제를 요청",
            "löschen", "dauerhaft löschen", "konto schliessen",
        ]
        for marker in deletion_markers:
            if marker in cleaned:
                return True, "DELETION"

        return None

    def _call_gemini(self, text: str) -> Optional[Tuple[bool, str]]:
        """Calls Gemini 3.8 Flash model to perform structured intent classification."""
        try:
            # We use urllib to avoid hard external SDK requirements while supporting standard Gemini API
            import json
            import urllib.request

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
            prompt = (
                "You are a strict data-privacy compliance classifier. "
                "Analyze the following user request and determine whether the user is explicitly requesting "
                "permanent account deletion/erasure of their account and personal data, OR requesting something else "
                "(such as marketing opt-out, email unsubscribe, data access inquiry under GDPR Art 15, data export under Art 20, "
                "or detail correction under Art 16).\n\n"
                f"User Request: {text}\n\n"
                "Return ONLY a JSON object with this exact format:\n"
                "{\n"
                '  "is_deletion": true or false,\n'
                '  "intent": "DELETION" or "MARKETING_OPT_OUT" or "DATA_ACCESS" or "DATA_EXPORT" or "RECTIFICATION" or "OTHER"\n'
                "}"
            )

            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.0,
                    "responseMimeType": "application/json",
                },
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                candidate = resp_data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(candidate)
                return bool(parsed.get("is_deletion", False)), str(parsed.get("intent", "OTHER"))
        except Exception:
            return None
