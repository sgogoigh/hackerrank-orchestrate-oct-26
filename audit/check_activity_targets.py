import csv

with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    rows = list(csv.reader(f))[1:]

targets = ['analytics_1895', 'account_3136', 'analytics_4566', 'account_5684', 'analytics_4574', 'account_3866', 'analytics_5335', 'account_6440', 'analytics_6077', 'account_5482']

for r in rows:
    for t in targets:
        if t in r[5] or t in r[7]:
            print(f"[{r[1]}] {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]}")
