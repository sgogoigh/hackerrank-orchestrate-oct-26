import csv

with open('dataset/system_activity.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        if r['target_system'] == 'account_service' and r['event_type'] == 'DELETE_RECORD':
            print(f"act={r['activity_id']} at={r['event_time']} src={r['source_system']} res={r['resource_id']} st={r['reported_result']} det={r['details']}")
            break
