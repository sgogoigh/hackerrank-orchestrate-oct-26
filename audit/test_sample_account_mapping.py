import csv
import json
from audit.build_account_map import user_to_account
from audit.build_email_account_map import email_to_account

with open('dataset/sample_deletion_requests.csv', 'r', encoding='utf-8') as f:
    sample_cases = list(csv.DictReader(f))

with open('dataset/sample_output.csv', 'r', encoding='utf-8') as f:
    golds = {r['case_id']: r for r in csv.DictReader(f)}

matches = 0
for c in sample_cases:
    cid = c['case_id']
    em = c['email'].lower()
    
    # Gold account
    g_steps = json.loads(golds[cid]['steps_json'])
    gold_accs = [s['resource_id'] for s in g_steps if s['system_id'] == 'account_service']
    
    # Look up in email_to_account
    found_acc = email_to_account.get(em)
    
    print(f"{cid} ({em}): Gold={gold_accs} | Found={found_acc}")
