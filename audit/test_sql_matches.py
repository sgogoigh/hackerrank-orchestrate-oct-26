import csv
import json
import re

# Load sample_deletion_requests
cases = []
with open('dataset/sample_deletion_requests.csv', 'r', encoding='utf-8') as f:
    cases = list(csv.DictReader(f))

# Let's inspect which cases have matches in these replica SQL files
import glob
sql_files = [
    'customer_data_read_replica_20260921.sql',
    'customer_data_failover_replica_20260920.sql',
    'customer_data_read_replica_20260827.sql',
    'customer_data_read_replica_20260802.sql',
    'customer_data_read_replica_20260708.sql',
    'customer_data_read_replica_20260613.sql',
    'customer_data_regional_replicas_20260519.sql',
    'customer_data_regional_replicas_20260424.sql',
    'customer_data_regional_replicas_20260330.sql',
    'customer_data_reporting_replica_20260305.sql',
    'customer_data_reporting_replica_20260208.sql',
]

for c in cases:
    cid = c['case_id']
    email = c['email'].strip().lower()
    aud_at = c['audit_at'].strip()
    req_at = c.get('requested_at', '').strip()
    
    # Search all sql files
    for fname in sql_files:
        path = f"dataset/evidence/databases/{fname}"
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if email in line.lower():
                    print(f"Match for {cid} ({email}) in {fname}:")
                    print(f"  {line.strip()[:140]}")
