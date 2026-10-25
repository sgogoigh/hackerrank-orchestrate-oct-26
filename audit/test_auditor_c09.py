from code.identity import IdentityResolver
from code.evidence_scanner import EvidenceScanner
from code.auditor import DeletionAuditor

id_resolver = IdentityResolver()
scanner = EvidenceScanner()
auditor = DeletionAuditor()

ident = id_resolver.resolve(email='k.appiah88@gmail.com')
resources = scanner.scan_subject_resources(ident, audit_at='2026-09-18T12:00:00Z', requested_at='2026-09-04T09:00:00Z', case_id='case_09')
status, steps = auditor.audit_case('case_09', True, resources)
print("Status:", status)
print("Steps:")
for s in steps:
    print(f"  [{s['phase']}] {s['system_id']}.{s['resource_id']} -> {s['operation']} ({s['state']}) ev='{s['evidence_id']}'")
