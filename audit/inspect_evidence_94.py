with open('dataset/evidence/logs/resource_lookup_trace_20260926_103856.log', 'r', encoding='utf-8') as f:
    for line in f:
        if '6645' in line or '5569' in line or 'audit_record' in line:
            print(line.strip())
