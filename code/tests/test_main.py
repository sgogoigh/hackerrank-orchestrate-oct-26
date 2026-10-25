"""Unit tests for the Main Orchestration Entry Point (code/main.py).

Verifies execution pipeline, output schema generation, ascending case_id sorting,
and steps_json formatting.
"""

import csv
import json
import tempfile
import unittest
from pathlib import Path
from code.main import run_pipeline


class TestMainPipeline(unittest.TestCase):
    """Test suite for run_pipeline in code/main.py."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.out_csv = Path(self.temp_dir.name) / "test_output.csv"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_run_pipeline_on_sample_requests(self):
        """Test running pipeline on sample_deletion_requests.csv produces valid output."""
        code = run_pipeline(
            input_path="dataset/sample_deletion_requests.csv",
            output_path=str(self.out_csv),
            dataset_dir="dataset",
        )
        self.assertEqual(code, 0)
        self.assertTrue(self.out_csv.exists())

        with open(self.out_csv, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            self.assertEqual(header, ["case_id", "deletion_status", "steps_json"])

            rows = list(reader)
            self.assertGreater(len(rows), 0)

            # Check ascending sort
            case_ids = [r[0] for r in rows]
            self.assertEqual(case_ids, sorted(case_ids))

            # Validate each row
            for case_id, status, steps_json in rows:
                self.assertIn(status, ("COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"))
                parsed = json.loads(steps_json)
                self.assertIsInstance(parsed, list)
                if status == "NOT_APPLICABLE":
                    self.assertEqual(parsed, [])
                else:
                    for idx, step in enumerate(parsed, start=1):
                        self.assertEqual(step["step_no"], idx)
                        self.assertIn(step["phase"], ("FINDING", "REMEDIATION", "VERIFICATION"))


if __name__ == "__main__":
    unittest.main()
