import csv
import json
import re
from pathlib import Path

user_to_account = {}

# 1. Check handover txt
for p in Path('dataset/evidence').rglob('*.txt'):
    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if '|' in line and 'account_' in line and 'user_' in line:
                m_acc = re.search(r'(account_\w+)', line)
                m_usr = re.search(r'(user_\w+)', line)
                if m_acc and m_usr:
                    user_to_account[m_usr.group(1)] = m_acc.group(1)

# 2. Check snapshot bundles
for p in Path('dataset/evidence/records').rglob('*.json'):
    try:
        data = json.load(open(p, 'r', encoding='utf-8'))
        for snap in data.get('snapshots', []):
            if snap.get('data_store') == 'account_service':
                for rec in snap.get('records', []):
                    rid = rec.get('resource_id')
                    cref = rec.get('customer_reference')
                    if rid and cref:
                        user_to_account[cref] = rid
    except:
        pass

# 3. Check logs for trace pairing between lookup_key/subject_ref and account_XXXX
for p in Path('dataset/evidence/logs').rglob('*.log'):
    traces = {}
    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m_tid = re.search(r'trace_id=(?:")?([a-zA-Z0-9_\-]+)', line) or re.search(r'requestId=(?:")?([a-zA-Z0-9_\-]+)', line)
            m_acc = re.search(r'(account_\w+)', line)
            m_usr = re.search(r'(user_\w+)', line)
            m_em = re.search(r'[\w\.-]+@[\w\.-]+', line)
            
            if m_tid:
                tid = m_tid.group(1)
                traces.setdefault(tid, {})
                if m_acc: traces[tid]['account'] = m_acc.group(1)
                if m_usr: traces[tid]['user'] = m_usr.group(1)
                if m_em: traces[tid]['email'] = m_em.group(0).lower()
                
    for tid, ctx in traces.items():
        acc = ctx.get('account')
        usr = ctx.get('user')
        if acc and usr:
            user_to_account[usr] = acc

print(f"Total mapped user -> account: {len(user_to_account)}")
for u, a in sorted(user_to_account.items())[:20]:
    print(f"  {u} -> {a}")
