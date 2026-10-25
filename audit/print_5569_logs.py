with open('dataset/evidence/logs/cloud_runtime_export_af_south_20260930.log', 'r', encoding='utf-8') as f:
    for line in f:
        if '5569' in line:
            print("[cloud]", line.strip())

with open('dataset/evidence/logs/resource_lookup_trace_20260926_103856.log', 'r', encoding='utf-8') as f:
    for line in f:
        if '5569' in line:
            print("[trace]", line.strip())
