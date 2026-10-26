import os
import shutil
import zipfile
from pathlib import Path

repo_dir = Path(".").resolve()
parent_dir = repo_dir.parent
staging_dir = parent_dir / "agent-trace"
zip_path = parent_dir / "agent-trace.zip"

print(f"Packaging agent traces into: {zip_path}")

# Clean up previous staging dir if present
if staging_dir.exists():
    shutil.rmtree(staging_dir)

staging_dir.mkdir(parents=True, exist_ok=True)
antigravity_dir = staging_dir / "antigravity"
antigravity_dir.mkdir(parents=True, exist_ok=True)

# 1. Copy conversation brain directories
appdata_brain = Path(r"C:\Users\sgogo\.gemini\antigravity-ide\brain")
conversations = [
    "fd4d42eb-4104-4ff3-bc1e-70f6c654735c",
    "5210c765-8f38-4176-93eb-2421d1e26b4a",
]

for cid in conversations:
    src = appdata_brain / cid
    dst = antigravity_dir / cid
    if src.exists():
        print(f"Copying conversation brain {cid}...")
        # Ignore huge video files or temp files if any, but include transcripts and artifacts
        def ignore_patterns(path, names):
            ignored = []
            for n in names:
                if n.endswith((".webp", ".tmp")):
                    ignored.append(n)
            return ignored
        shutil.copytree(src, dst, ignore=ignore_patterns)

# 2. Copy conversation SQLite database files
appdata_conv = Path(r"C:\Users\sgogo\.gemini\antigravity-ide\conversations")
conv_db_dir = antigravity_dir / "conversations_db"
conv_db_dir.mkdir(parents=True, exist_ok=True)

for cid in conversations:
    db_file = appdata_conv / f"{cid}.db"
    if db_file.exists():
        print(f"Copying conversation DB {cid}.db...")
        shutil.copy2(db_file, conv_db_dir / f"{cid}.db")

# 3. Copy running log.txt
repo_log = repo_dir / "log.txt"
if repo_log.exists():
    print("Copying repository log.txt...")
    shutil.copy2(repo_log, staging_dir / "log.txt")

# 4. Zip the agent-trace directory
print("Creating zip archive...")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(staging_dir):
        for f in files:
            full_path = Path(root) / f
            rel_path = full_path.relative_to(staging_dir)
            archive_name = Path("agent-trace") / rel_path
            zipf.write(full_path, archive_name)

print("Verifying archive...")
with zipfile.ZipFile(zip_path, "r") as zipf:
    namelist = zipf.namelist()
    print(f"Total files in agent-trace.zip: {len(namelist)}")
    print(f"Uncompressed size: {sum(i.file_size for i in zipf.infolist()) / (1024*1024):.2f} MB")
    print(f"Compressed size: {zip_path.stat().st_size / (1024*1024):.2f} MB")
    
    # Check that transcript.jsonl is present
    transcripts = [n for n in namelist if "transcript.jsonl" in n]
    print(f"Transcripts found: {transcripts}")
    assert len(transcripts) >= 2, "Expected at least 2 transcript.jsonl files"

# Clean up staging directory
shutil.rmtree(staging_dir)
print(f"Successfully packaged agent-trace.zip at {zip_path}!")

