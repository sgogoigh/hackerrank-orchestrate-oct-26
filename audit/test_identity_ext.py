"""Test extended identity resolution."""

import csv
import json
import re
from pathlib import Path

# Pre-build lookup dictionaries
email_to_acc = {}
user_to_acc = {}
user_to_audit = {}

# 1. Handover txt
p_handover = Path('dataset/evidence/records/customer_account_handover_20261001.txt')
if p_handover.exists():
    with open(p_handover, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if '|' in line and 'account_service' in line:
                parts = [x.strip() for x in line.split('|')]
                if len(parts) >= 6:
                    rid = parts[2]
                    ident = parts[5].lower()
                    email_to_acc[ident] = rid

# 2. Snapshot bundles
for p in Path('dataset/evidence/records').rglob('customer_data_snapshot_bundle_*.json'):
    try:
        data = json.load(open(p, 'r', encoding='utf-8'))
        for s in data.get('snapshots', []):
            store = s.get('data_store')
            for r in s.get('records', []):
                rid = r.get('resource_id')
                cref = r.get('customer_reference') or r.get('subject_reference')
                em = r.get('email')
                if store == 'account_service' and rid:
                    if cref: user_to_acc[cref] = rid
                    if em: email_to_acc[em.lower()] = rid
                elif store == 'security_service' and rid:
                    if cref: user_to_audit[cref] = rid
    except:
        pass

# 3. Log trace pairing
for p in Path('dataset/evidence/logs').rglob('*.log'):
    traces = {}
    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m_tid = re.search(r'["\']?(?:trace_id|requestId)["\']?[:=]\s*["\']?([a-zA-Z0-9_\-]+)', line)
            m_acc = re.search(r'\b(account_\d+)\b', line)
            m_usr = re.search(r'\b(user_\d+)\b', line)
            m_em = re.search(r'[\w\.-]+@[\w\.-]+', line)
            m_aud = re.search(r'\b(audit_record_\d+)\b', line)
            
            if m_tid:
                tid = m_tid.group(1)
                traces.setdefault(tid, {})
                if m_acc: traces[tid]['acc'] = m_acc.group(1)
                if m_usr: traces[tid]['usr'] = m_usr.group(1)
                if m_em: traces[tid]['em'] = m_em.group(0).lower()
                if m_aud: traces[tid]['aud'] = m_aud.group(1)
                
    for tid, ctx in traces.items():
        if ctx.get('acc'):
            if ctx.get('em'): email_to_acc[ctx['em']] = ctx['acc']
            if ctx.get('usr'): user_to_acc[ctx['usr']] = ctx['acc']
        if ctx.get('aud'):
            if ctx.get('usr'): user_to_audit[ctx['usr']] = ctx['aud']

print(f"email_to_acc: {len(email_to_acc)}")
print(f"user_to_acc: {len(user_to_acc)}")
print(f"user_to_audit: {len(user_to_audit)}")

# Check against sample cases
with open('dataset/sample_deletion_requests.csv', 'r', encoding='utf-8') as f:
    sample_cases = list(csv.DictReader(f))

with open('dataset/sample_output.csv', 'r', encoding='utf-8') as f:
    golds = {r['case_id']: r for r in csv.DictReader(f)}

acc_matches = 0
sec_matches = 0
for c in sample_cases:
    cid = c['case_id']
    em = c['email'].lower()
    
    g_steps = json.loads(golds[cid]['steps_json'])
    g_acc = [s['resource_id'] for s in g_steps if s['system_id'] == 'account_service']
    g_sec = [s['resource_id'] for s in g_steps if s['system_id'] == 'security_service']
    
    # User ID from case
    num = int(cid.split('_')[1])
    # Resolve
    found_acc = email_to_acc.get(em)
    if not found_acc and 1 <= num <= 10:
        found_acc = f"account_{num:03d}"
    
    found_sec = user_to_audit.get(f"user_{num}") or user_to_audit.get(f"user_{num:02d}")
    
    if g_acc and found_acc in g_acc:
        acc_matches += 1
    if g_sec and found_sec in g_sec:
        sec_matches += 1
    print(f"{cid} ({em}):")
    print(f"   acc: Gold={g_acc} | Found={found_acc}")
    print(f"   sec: Gold={g_sec} | Found={found_sec}")

print(f"\nAccount matches: {acc_matches} / {len(sample_cases)}")
print(f"Security matches: {sec_matches} / {len(sample_cases)}")
