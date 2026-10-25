"""Prototype test for Iteration 7 enhancements."""

import csv
import json
from datetime import datetime
from code.evidence_scanner import EvidenceScanner
from code.identity import IdentityResolver
from code.auditor import DeletionAuditor

resolver = IdentityResolver()
scanner = EvidenceScanner()
auditor = DeletionAuditor()

# Pre-build account and audit_record mappings from system_activity and evidence
with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    acts = list(csv.reader(f))[1:]

# Load snapshot bundle 20260917 explicitly
with open('dataset/evidence/records/customer_data_snapshot_bundle_20260917.json', 'r', encoding='utf-8') as f:
    bundle_92 = json.load(f)

# Map user_id to audit_record in bundle_92
user_to_audit_bundle = {}
for s in bundle_92.get('snapshots', []):
    if s.get('data_store') == 'security_service':
        for r in s.get('records', []):
            cref = r.get('subject_reference')
            rid = r.get('resource_id')
            if cref and rid:
                user_to_audit_bundle[cref] = rid

# Map user_id to audit_record in evidence_51
with open('dataset/evidence/records/customer_data_snapshot_bundle_20260915.json', 'r', encoding='utf-8') as f:
    bundle_51 = json.load(f)
for s in bundle_51.get('snapshots', []):
    if s.get('data_store') == 'security_service':
        for r in s.get('records', []):
            cref = r.get('subject_reference')
            rid = r.get('resource_id')
            if cref and rid:
                user_to_audit_bundle[cref] = rid

print(f"Total user -> audit_record in bundles: {len(user_to_audit_bundle)}")
for u, a in sorted(user_to_audit_bundle.items()):
    print(f"  {u} -> {a}")
