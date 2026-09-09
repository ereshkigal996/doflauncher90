import pymysql
import json

# 数据库配置
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 13306,
    'user': 'root',
    'password': 'db_ed372bfa36051308258d2a75f431e91b',
    'database': 'dnf_local',
    'charset': 'utf8mb4'
}

def main():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # 1. 查询最新的邮件
    print("=== 最新的邮件（前3条）===")
    cursor.execute("SELECT * FROM dnf_mails ORDER BY created_at DESC LIMIT 3")
    for row in cursor.fetchall():
        print(json.dumps(row, ensure_ascii=False, default=str, indent=2))
        print()
    
    # 2. 查询最新的邮件附件
    print("=== 最新的邮件附件（前3条）===")
    cursor.execute("SELECT * FROM dnf_mail_attachments ORDER BY character_id DESC, mail_id DESC LIMIT 3")
    for row in cursor.fetchall():
        # 处理raw_entry二进制数据
        row_copy = row.copy()
        if 'raw_entry' in row_copy and row_copy['raw_entry']:
            raw_data = row_copy['raw_entry']
            if isinstance(raw_data, bytes):
                row_copy['raw_entry_hex'] = raw_data.hex()
                row_copy['raw_entry'] = f"<binary data, length={len(raw_data)}>"
        print(json.dumps(row_copy, ensure_ascii=False, default=str, indent=2))
        print()
    
    # 3. 查询最新的邮件附件extra数据
    print("=== 最新的邮件附件extra数据（前20条）===")
    cursor.execute("SELECT * FROM dnf_mail_attachment_extra ORDER BY character_id DESC, mail_id DESC LIMIT 20")
    for row in cursor.fetchall():
        print(json.dumps(row, ensure_ascii=False, default=str, indent=2))
    print()
    
    # 4. 查询最新的邮件元数据
    print("=== 最新的邮件元数据（前10条）===")
    cursor.execute("SELECT * FROM dnf_mail_metadata ORDER BY character_id DESC, mail_id DESC LIMIT 10")
    for row in cursor.fetchall():
        print(json.dumps(row, ensure_ascii=False, default=str, indent=2))
    print()
    
    # 5. 查询最新的背包装备
    print("=== 最新的背包装备（前3条）===")
    cursor.execute("SELECT * FROM dnf_inventory_items WHERE collection_name = 'inventory' ORDER BY character_id DESC LIMIT 3")
    for row in cursor.fetchall():
        # 处理raw_entry二进制数据
        row_copy = row.copy()
        if 'raw_entry' in row_copy and row_copy['raw_entry']:
            raw_data = row_copy['raw_entry']
            if isinstance(raw_data, bytes):
                row_copy['raw_entry_hex'] = raw_data.hex()
                row_copy['raw_entry'] = f"<binary data, length={len(raw_data)}>"
        print(json.dumps(row_copy, ensure_ascii=False, default=str, indent=2))
        print()
    
    # 6. 查询最新的背包装备extra数据
    print("=== 最新的背包装备extra数据（前20条）===")
    cursor.execute("SELECT * FROM dnf_inventory_item_extra WHERE collection_name = 'inventory' ORDER BY character_id DESC LIMIT 20")
    for row in cursor.fetchall():
        print(json.dumps(row, ensure_ascii=False, default=str, indent=2))
    print()
    
    conn.close()

if __name__ == '__main__':
    main()
