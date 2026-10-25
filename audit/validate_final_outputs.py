import csv
import json
from pathlib import Path

for target in ["output.csv", "dataset/output.csv"]:
    p = Path(target)
    assert p.exists(), f"{target} does not exist!"
    with open(p, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    
    print(f"\n--- Verifying {target} ---")
    print(f"Total rows: {len(reader)}")
    assert len(reader) == 518, f"Expected 518 rows, got {len(reader)}"
    
    # Check headers
    with open(p, "r", encoding="utf-8") as f:
        header_line = f.readline().strip()
    assert header_line == "case_id,deletion_status,steps_json", f"Bad header: {header_line}"
    
    # Check sorting
    case_ids = [r["case_id"] for r in reader]
    assert case_ids == sorted(case_ids), "Rows not sorted ascending by case_id!"
    print(f"Sorting verified: {case_ids[0]} to {case_ids[-1]}")
    
    # Check statuses and JSON validity
    statuses = {}
    for r in reader:
        st = r["deletion_status"]
        statuses[st] = statuses.get(st, 0) + 1
        assert st in ("COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"), f"Invalid status: {st}"
        steps = json.loads(r["steps_json"])
        assert isinstance(steps, list), "steps_json is not a list!"
        if st == "NOT_APPLICABLE":
            assert len(steps) == 0, f"Expected [] for NOT_APPLICABLE, got {steps}"
        else:
            for i, s in enumerate(steps, start=1):
                assert s["step_no"] == i, f"step_no mismatch: expected {i}, got {s['step_no']}"
                assert s["phase"] in ("FINDING", "REMEDIATION", "VERIFICATION")
                assert "system_id" in s and "resource_id" in s and "operation" in s and "state" in s and "evidence_id" in s

    print(f"Status distribution: {statuses}")
    print(f"Validation successful for {target}!")

# Verify dataset/sample_output.csv git diff
