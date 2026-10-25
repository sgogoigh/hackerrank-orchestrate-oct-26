with open('dataset/evidence/logs/structured_service_events_eu_west_20260918.log', 'r', encoding='utf-8') as f:
    for line in f:
        if 'account_3960' in line:
            print(line.strip())
