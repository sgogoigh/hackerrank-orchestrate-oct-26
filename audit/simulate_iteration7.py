"""Simulate Iteration 7 changes and measure sequence accuracy improvement."""

import csv
import json
import re
from datetime import datetime
from code.identity import IdentityResolver
from code.evidence_scanner import EvidenceScanner
from code.auditor import DeletionAuditor
from code.evaluation.main import evaluate_predictions

# Let's inspect the 14 cases with the updated mappings
with open("dataset/sample_output.csv", "r", encoding="utf-8") as f:
    golds = {r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"])) for r in csv.DictReader(f)}

print("Starting simulation...")
