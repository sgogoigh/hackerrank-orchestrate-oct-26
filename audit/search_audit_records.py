with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    for line in f:
        if 'audit_record_4902' in line or 'audit_record_6645' in line or 'audit_record_5569' in line or 'audit_record_4128' in line:
            print(line.strip())
