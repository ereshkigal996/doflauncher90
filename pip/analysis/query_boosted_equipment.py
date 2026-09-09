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
    
    # 1. 查询最新的邮件（前5条）
    print("=== 最新的邮件（前5条）===")
    cursor.execute("SELECT * FROM dnf_mails ORDER BY created_at DESC LIMIT 5")
    for row in cursor.fetchall():
        print(f"邮件ID: {row['mail_id']}, 标题: {row['title']}, 内容: {row['body']}")
        print(f"  收件人: {row['recipient_name']}, 创建时间: {row['created_at']}")
        print(f"  read_flag: {row['read_flag']}, claimed_flag: {row['claimed_flag']}, deleted_flag: {row['deleted_flag']}")
        print()
    
    # 2. 查询最新的邮件附件（前5条）
    print("=== 最新的邮件附件（前5条）===")
    cursor.execute("SELECT * FROM dnf_mail_attachments ORDER BY character_id DESC, mail_id DESC LIMIT 5")
    for row in cursor.fetchall():
        print(f"邮件ID: {row['mail_id']}, 物品ID: {row['item_id']}, 数量: {row['item_count']}")
        print(f"  bind_flag: {row['bind_flag']}")
        if row['raw_entry']:
            raw_data = row['raw_entry']
            print(f"  raw_entry长度: {len(raw_data)} 字节")
            print(f"  raw_entry十六进制: {raw_data.hex()}")
            # 分析raw_entry的各个部分
            print(f"  0-1字节: {raw_data[0]:02x} {raw_data[1]:02x}")
            print(f"  2-5字节(物品ID): {raw_data[2:6].hex()}")
            print(f"  6-9字节(quality_seed): {raw_data[6:10].hex()}")
            print(f"  10字节: {raw_data[10]:02x}")
            print(f"  11字节(耐久度): {raw_data[11]:02x}")
            print(f"  12-20字节: {raw_data[12:21].hex()}")
            print(f"  21-30字节: {raw_data[21:31].hex()}")
            # 检查哪些字节非0
            non_zero = []
            for i in range(12, len(raw_data)):
                if raw_data[i] != 0:
                    non_zero.append((i, raw_data[i]))
            if non_zero:
                print(f"  12字节后非0的位置: {non_zero}")
            else:
                print(f"  12字节后全为0")
        else:
            print(f"  raw_entry: NULL")
        print()
    
    # 3. 查询最新的邮件附件extra数据（前30条）
    print("=== 最新的邮件附件extra数据（前30条）===")
    cursor.execute("SELECT * FROM dnf_mail_attachment_extra ORDER BY character_id DESC, mail_id DESC LIMIT 30")
    current_mail_id = None
    for row in cursor.fetchall():
        if row['mail_id'] != current_mail_id:
            current_mail_id = row['mail_id']
            print(f"\n--- 邮件ID: {current_mail_id} ---")
        print(f"  {row['extra_key']}: {row['extra_value']}")
    
    print()
    
    # 4. 查询最新的邮件元数据
    print("=== 最新的邮件元数据 ===")
    cursor.execute("SELECT * FROM dnf_mail_metadata ORDER BY character_id DESC, mail_id DESC LIMIT 15")
    current_mail_id = None
    for row in cursor.fetchall():
        if row['mail_id'] != current_mail_id:
            current_mail_id = row['mail_id']
            print(f"\n--- 邮件ID: {current_mail_id} ---")
        print(f"  {row['metadata_key']}: {row['metadata_value']}")
    
    conn.close()

if __name__ == '__main__':
    main()
