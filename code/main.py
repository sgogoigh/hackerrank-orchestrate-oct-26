"""Main Orchestration Entry Point for the Ghost Data Still Exists Deletion-Audit Agent.

Reads dataset/deletion_requests.csv, applies multilingual intent classification,
reconstructs identity profiles, verifies multimodal evidence at audit_at,
evaluates policy rules, and generates output.csv.
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import List, Tuple

from code.auditor import DeletionAuditor
from code.classifier import IntentClassifier
from code.evidence_scanner import EvidenceScanner
from code.identity import IdentityResolver


def run_pipeline(
    input_path: str = "dataset/deletion_requests.csv",
    output_path: str = "output.csv",
    dataset_dir: str = "dataset",
) -> int:
    """Executes the full deletion-audit pipeline."""
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: Input file {input_path} does not exist.", file=sys.stderr)
        return 1

    print(f"Starting Deletion-Audit Pipeline on: {input_path}")

    # Initialize pipeline components
    classifier = IntentClassifier(cache_path=f"{dataset_dir}/cache/intent_cache.json")
    resolver = IdentityResolver(
        identities_path=f"{dataset_dir}/user_identities.csv",
        audit_log_path=f"{dataset_dir}/user_audit_log.csv",
        activity_path=f"{dataset_dir}/system_activity.csv",
    )
    scanner = EvidenceScanner(dataset_dir=dataset_dir)
    auditor = DeletionAuditor()

    results: List[Tuple[str, str, str]] = []

    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            case_id = row["case_id"].strip()
            email = row["email"].strip()
            audit_at = row["audit_at"].strip()
            request_text = row["request_text"].strip()

            # 1. Filter 1: Multilingual Intent Classification
            is_deletion = classifier.is_deletion_request(case_id, request_text)
            if not is_deletion:
                results.append((case_id, "NOT_APPLICABLE", "[]"))
                continue

            # 2. Identity Resolution
            identity = resolver.resolve(email)
            if not identity:
                # If email not found in records, treat as absent / complete
                results.append((case_id, "NOT_APPLICABLE", "[]"))
                continue

            # 3. Evidence Extraction at audit_at with temporal lower bound requested_at
            requested_at = row.get("requested_at", "").strip()
            resources = scanner.scan_subject_resources(
                identity=identity,
                audit_at=audit_at,
                requested_at=requested_at,
                case_id=case_id,
            )

            # 4. Policy Evaluation & Step Sequencing
            status, steps = auditor.audit_case(case_id, is_deletion, resources, identity=identity)
            steps_json_str = json.dumps(steps, separators=(",", ":"), ensure_ascii=False)
            results.append((case_id, status, steps_json_str))


    # Sort results ascending by case_id
    results.sort(key=lambda x: x[0])

    # Write output to target output_path
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "deletion_status", "steps_json"])
        for case_id, status, steps_json in results:
            writer.writerow([case_id, status, steps_json])

    # Also mirror to dataset/output.csv if root output.csv was target
    if output_path == "output.csv":
        mirror_file = Path(f"{dataset_dir}/output.csv")
        mirror_file.parent.mkdir(parents=True, exist_ok=True)
        with open(mirror_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["case_id", "deletion_status", "steps_json"])
            for case_id, status, steps_json in results:
                writer.writerow([case_id, status, steps_json])

    print(f"Pipeline finished successfully. Wrote {len(results)} rows to {output_path}.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Ghost Data Still Exists Deletion-Audit Agent")
    parser.add_argument("--samples", action="store_true", help="Run on sample_deletion_requests.csv")
    parser.add_argument("--input", type=str, default=None, help="Custom input CSV file path")
    parser.add_argument("--output", type=str, default="output.csv", help="Target output CSV file path")
    parser.add_argument("--dataset-dir", type=str, default="dataset", help="Dataset directory path")

    args = parser.parse_args()

    input_file = args.input
    if not input_file:
        input_file = f"{args.dataset_dir}/sample_deletion_requests.csv" if args.samples else f"{args.dataset_dir}/deletion_requests.csv"

    sys.exit(run_pipeline(input_file, args.output, args.dataset_dir))


if __name__ == "__main__":
    main()
