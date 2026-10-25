from code.identity import IdentityResolver

class TestResolver(IdentityResolver):
    def _load_evidence_linkages(self):
        super()._load_evidence_linkages()
        print("After super _load_evidence_linkages, user_541:", self.user_to_audit_record.get('user_541'))

r = TestResolver()
