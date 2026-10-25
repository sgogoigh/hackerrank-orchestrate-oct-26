with open('dataset/evidence/logs/service_events_ap_south_20260915.log', 'r', encoding='utf-8') as f:
    for line in f:
        if 'tr-9923588' in line or 'tr-3789306' in line:
            print(line.strip())
