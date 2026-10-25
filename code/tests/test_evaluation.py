"""Unit tests for the Evaluation Suite (code/evaluation/main.py).

Verifies accuracy calculations against golden answers and generation of
evaluation_report.md and usage_report.md.
"""

import tempfile
import unittest
from pathlib import Path
from code.evaluation.main import evaluate_predictions


class TestEvaluationSuite(unittest.TestCase):
    """Test suite for evaluate_predictions."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.eval_report = Path(self.temp_dir.name) / "eval_report.md"
        self.usage_report = Path(self.temp_dir.name) / "usage_report.md"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_golden_self_evaluation_scores_100_percent(self):
        """Evaluating sample_output.csv against itself must yield 100% on all metrics."""
        metrics = evaluate_predictions(
            pred_path="dataset/sample_output.csv",
            golden_path="dataset/sample_output.csv",
            eval_report_path=str(self.eval_report),
            usage_report_path=str(self.usage_report),
        )

        self.assertEqual(metrics["status_accuracy"], 100.0)
        self.assertEqual(metrics["sequence_accuracy"], 100.0)
        self.assertEqual(metrics["step_precision"], 100.0)
        self.assertEqual(metrics["step_recall"], 100.0)
        self.assertEqual(metrics["step_f1"], 100.0)

        # Confirm reports were written
        self.assertTrue(self.eval_report.exists())
        self.assertTrue(self.usage_report.exists())
        self.assertGreater(self.eval_report.stat().st_size, 100)
        self.assertGreater(self.usage_report.stat().st_size, 100)


if __name__ == "__main__":
    unittest.main()
