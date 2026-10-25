from code.identity import IdentityResolver
from code.evidence_scanner import EvidenceScanner

id_resolver = IdentityResolver()
scanner = EvidenceScanner()

ident = id_resolver.resolve(email='k.appiah88@gmail.com')
print("Ident:", ident)
resources = scanner.scan_subject_resources(ident, audit_at='2026-09-18T12:00:00Z', requested_at='2026-09-04T09:00:00Z', case_id='case_09')
print(f"Scanned {len(resources)} resources:")
for r in resources:
    print(f"  {r.system_id}.{r.resource_id} -> {r.state} (ev={r.evidence_id})")
