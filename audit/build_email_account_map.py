import csv
import json
import re
from pathlib import Path

email_to_account = {}

# Check logs for trace pairing between email and account_XXXX
for p in Path('dataset/evidence/logs').rglob('*.log'):
    traces = {}
    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m_tid = re.search(r'["\']?(?:trace_id|requestId)["\']?[:=]\s*["\']?([a-zA-Z0-9_\-]+)', line)
            m_acc = re.search(r'\b(account_\d+)\b', line)
            m_em = re.search(r'[\w\.-]+@[\w\.-]+', line)
            
            if m_tid:
                tid = m_tid.group(1)
                traces.setdefault(tid, {})
                if m_acc: traces[tid]['account'] = m_acc.group(1)
                if m_em: traces[tid]['email'] = m_em.group(0).lower()
                
    for tid, ctx in traces.items():
        acc = ctx.get('account')
        em = ctx.get('email')
        if acc and em:
            email_to_account[em] = acc

print(f"Total mapped email -> account: {len(email_to_account)}")
for em, a in sorted(email_to_account.items())[:20]:
    print(f"  {em} -> {a}")
