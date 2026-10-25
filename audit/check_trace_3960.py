with open('dataset/evidence/logs/structured_service_events_eu_west_20260918.log', 'r', encoding='utf-8') as f:
    for line in f:
        if 'tr-1463969' in line:
            print(line.strip())
