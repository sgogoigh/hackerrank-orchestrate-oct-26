from code.identity import IdentityResolver

resolver = IdentityResolver()
print("user_541:", resolver.user_to_audit_record.get('user_541'))
print("user_542:", resolver.user_to_audit_record.get('user_542'))
print("user_21:", resolver.user_to_audit_record.get('user_21'))
print("user_25:", resolver.user_to_audit_record.get('user_25'))
