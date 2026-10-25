import csv
from datetime import datetime

def parse_iso(ts):
    if not ts: return datetime.min
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    acts = list(csv.DictReader(f))

worker_acts = [a for a in acts if a['source_system'] == 'deletion_worker']

# Cluster activities that occur within 30 minutes of each other
clusters = []
curr_cluster = []
for a in sorted(worker_acts, key=lambda x: x['event_time']):
    if not curr_cluster:
        curr_cluster.append(a)
    else:
        diff = (parse_iso(a['event_time']) - parse_iso(curr_cluster[-1]['event_time'])).total_seconds()
        if diff <= 3600:
            curr_cluster.append(a)
        else:
            clusters.append(curr_cluster)
            curr_cluster = [a]
if curr_cluster:
    clusters.append(curr_cluster)

print(f"Total deletion worker clusters: {len(clusters)}")
for idx, cl in enumerate(clusters[-15:]):
    accs = [x['resource_id'] for x in cl if x['target_system'] == 'account_service']
    anas = [x['resource_id'] for x in cl if x['target_system'] == 'analytics_platform']
    sec = [x['resource_id'] for x in cl if x['target_system'] == 'security_service']
    ident = [x['resource_id'] for x in cl if x['target_system'] == 'identity_service']
    print(f"Cluster {idx} ({cl[0]['event_time']} to {cl[-1]['event_time']}):")
    print(f"  accs={accs}")
    print(f"  anas={anas}")
    print(f"  ident={ident}")
