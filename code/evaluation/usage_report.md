# Token Usage and Cost Report - Ghost Data Still Exists

## 1. Model Providers and Call Summary

| Provider | Model Identifier | Task | Temperature | Call Count |
|---|---|---|---|---|
| **Google Gemini** | `gemini-3.8-flash` | Multilingual Request Intent Classification | 0.0 | 32 |

---

## 2. Token Breakdown & Cost Estimates

*Estimated using Gemini 3.8 Flash pricing ($0.075 / 1M input tokens, $0.30 / 1M output tokens).*

| Metric | Per-Request Average | Full Run (32 Requests) |
|---|---|---|
| **Input Tokens** | ~140 tokens | ~4,480 tokens |
| **Output Tokens** | ~25 tokens | ~800 tokens |
| **Total Tokens** | ~165 tokens | ~5,280 tokens |
| **Estimated Cost** | < $0.00002 | < $0.0100 |

---

## 3. Optimization and Caching Strategy

* **Local Disk Caching:** `dataset/cache/intent_cache.json` caches model classifications. Subsequent pipeline executions run with **0 additional model calls** and **$0.00 incremental cost**.
* **Zero Model Calls for Deterministic Stages:** Identity resolution, evidence scanning, rule enforcement, and step sorting are executed entirely deterministically via Python algorithms, minimizing token expenditure while maximizing accuracy.
