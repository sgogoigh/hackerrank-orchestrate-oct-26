with open('dataset/evidence/logs/service_events_ap_south_20260915.log', 'r', encoding='utf-8') as f:
    for line in f:
        if 'user_18' in line or 'user_20' in line:
            print(line.strip())
