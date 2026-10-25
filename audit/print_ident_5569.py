with open('dataset/user_identities.csv', 'r', encoding='utf-8') as f:
    for line in f:
        if '5569' in line:
            print(line.strip())
