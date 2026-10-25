from code.identity import IdentityResolver
r = IdentityResolver()
print("user_to_audit_record keys count:", len(r.user_to_audit_record))
print("Sample keys:", list(r.user_to_audit_record.items())[:10])
print("user_541:", r.user_to_audit_record.get('user_541'))
