with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    for line in f:
        if '6645' in line or '5569' in line:
            print(line.strip())
