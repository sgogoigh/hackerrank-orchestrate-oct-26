import csv

with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    rows = list(csv.reader(f))[1:]

targets = ['account_5521', 'account_5037', 'account_410', 'account_6440', 'account_7012', 'account_3866', 'account_5482', 'account_4163', 'account_4857', 'account_8858', 'account_3136', 'account_5684', 'account_5334']

for r in rows:
    if r[5] in targets:
        print(f"[{r[1]}] act_id={r[0]} op={r[2]} actor={r[3]} sys={r[4]} res={r[5]} st={r[6]} | details={r[7]}")
