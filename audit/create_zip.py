import os
import zipfile
from pathlib import Path

repo_dir = Path(".").resolve()
parent_dir = repo_dir.parent
zip_path = parent_dir / "hackerrank-orchestrate-october26.zip"

print(f"Creating zip from: {repo_dir}")
print(f"Destination: {zip_path}")

exclude_dirs = {"audit", ".git", "__pycache__", ".pytest_cache"}

count = 0
total_size = 0

with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(repo_dir):
        # Filter out excluded directories in-place so os.walk doesn't recurse into them
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        # Check if root is inside any excluded dir
        rel_root = Path(root).relative_to(repo_dir)
        if any(part in exclude_dirs for part in rel_root.parts):
            continue

        for file in files:
            if file.endswith((".pyc", ".zip")):
                continue
            full_file_path = Path(root) / file
            rel_file_path = full_file_path.relative_to(repo_dir)
            
            # Make sure audit/ is not in the relative path
            if "audit" in rel_file_path.parts:
                continue

            # Store inside hackerrank-orchestrate-october26/ inside the zip
            archive_name = Path("hackerrank-orchestrate-october26") / rel_file_path
            zipf.write(full_file_path, archive_name)
            count += 1
            total_size += full_file_path.stat().st_size

print(f"Successfully created zip file!")
print(f"  Total files archived: {count}")
print(f"  Uncompressed size: {total_size / (1024*1024):.2f} MB")
print(f"  Compressed zip size: {zip_path.stat().st_size / (1024*1024):.2f} MB")

# Verify the zip archive does not contain audit/
with zipfile.ZipFile(zip_path, "r") as zipf:
    names = zipf.namelist()
    audit_files = [n for n in names if "/audit/" in n or n.endswith("/audit") or n.startswith("audit/")]
    print(f"Audit files in zip: {len(audit_files)}")
    assert len(audit_files) == 0, f"Error: Found audit files in zip: {audit_files}"
    print("Verification passed: ZERO audit files in the ZIP archive!")
