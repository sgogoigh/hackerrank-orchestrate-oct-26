with open('dataset/evidence/databases/customer_data_inventory_20260905.sql', 'r', encoding='utf-8') as f:
    for line in f:
        if 'audit_record' in line or 'user_18' in line or 'user_20' in line:
            print("[20260905]", line.strip())

with open('dataset/evidence/databases/customer_data_inventory_20260916.sql', 'r', encoding='utf-8') as f:
    for line in f:
        if 'audit_record' in line or 'user_18' in line or 'user_20' in line:
            print("[20260916]", line.strip())
