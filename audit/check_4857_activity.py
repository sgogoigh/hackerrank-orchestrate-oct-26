import csv

with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    rows = list(csv.reader(f))[1:]

for r in rows:
    if 'account_4857' in r[5] or 'account_8858' in r[5]:
        print(f"[{r[1]}] {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]}")
