import csv

with open("dataset/evidence_files.csv", "r", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["file_id"] in ("evidence_12", "evidence_54"):
            print(r)






















