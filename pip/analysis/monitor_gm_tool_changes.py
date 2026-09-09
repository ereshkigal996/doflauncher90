import pymysql
import json
import time
import os

# 数据库配置
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 13306,
    'user': 'root',
    'password': 'db_ed372bfa36051308258d2a75f431e91b',
    'database': 'dnf_local',
    'charset': 'utf8mb4'
}

WAIT_TIME = 60  # 等待时间（秒），用户在这段时间内使用原版GM工具发放装备

def get_db_snapshot():
    """获取数据库快照（邮件相关的表）"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    snapshot = {}
    
    # 邮件主表
    cursor.execute('SELECT * FROM dnf_mails ORDER BY created_at DESC LIMIT 30')
    snapshot['dnf_mails'] = cursor.fetchall()
    
    # 邮件附件表
    cursor.execute('SELECT * FROM dnf_mail_attachments ORDER BY character_id DESC, mail_id DESC LIMIT 30')
    snapshot['dnf_mail_attachments'] = cursor.fetchall()
    
    # 邮件附件extra表
    cursor.execute('SELECT * FROM dnf_mail_attachment_extra LIMIT 30')
    snapshot['dnf_mail_attachment_extra'] = cursor.fetchall()
    
    # 邮件元数据表
    cursor.execute('SELECT * FROM dnf_mail_metadata LIMIT 30')
    snapshot['dnf_mail_metadata'] = cursor.fetchall()
    
    # 邮箱表
    cursor.execute('SELECT * FROM dnf_mailboxes LIMIT 30')
    snapshot['dnf_mailboxes'] = cursor.fetchall()
    
    # 背包装备表（最近的20条）
    cursor.execute("SELECT * FROM dnf_inventory_items WHERE collection_name = 'inventory' ORDER BY character_id DESC LIMIT 20")
    snapshot['dnf_inventory_items'] = cursor.fetchall()
    
    # 背包装备extra表（最近的30条）
    cursor.execute("SELECT * FROM dnf_inventory_item_extra WHERE collection_name = 'inventory' ORDER BY character_id DESC LIMIT 30")
    snapshot['dnf_inventory_item_extra'] = cursor.fetchall()
    
    conn.close()
    return snapshot

def compare_snapshots(before, after):
    """对比两个快照，找出变化"""
    changes = {}
    
    for table_name in before.keys():
        before_data = before.get(table_name, [])
        after_data = after.get(table_name, [])
        
        # 生成唯一ID的函数
        def get_uid(item, table_name):
            if table_name == 'dnf_mails':
                return f"{item.get('character_id')}_{item.get('mail_id')}"
            elif table_name == 'dnf_mail_attachments':
                return f"{item.get('character_id')}_{item.get('mail_id')}_{item.get('attachment_index')}"
            elif table_name == 'dnf_mail_attachment_extra':
                return f"{item.get('character_id')}_{item.get('mail_id')}_{item.get('attachment_index')}_{item.get('extra_key')}"
            elif table_name == 'dnf_mail_metadata':
                return f"{item.get('character_id')}_{item.get('mail_id')}_{item.get('metadata_key')}"
            elif table_name == 'dnf_mailboxes':
                return f"{item.get('character_id')}"
            elif table_name == 'dnf_inventory_items':
                return f"{item.get('character_id')}_{item.get('collection_name')}_{item.get('entry_key')}"
            elif table_name == 'dnf_inventory_item_extra':
                return f"{item.get('character_id')}_{item.get('collection_name')}_{item.get('entry_key')}_{item.get('extra_key')}"
            else:
                return str(item)
        
        # 找出新增的数据
        before_ids = set()
        for item in before_data:
            before_ids.add(get_uid(item, table_name))
        
        new_items = []
        for item in after_data:
            uid = get_uid(item, table_name)
            if uid not in before_ids:
                new_items.append(item)
        
        if new_items:
            changes[table_name] = new_items
    
    return changes

def main():
    print("=== 原版GM工具数据库变化监控脚本 ===")
    print()
    print(f"脚本将等待 {WAIT_TIME} 秒，请在这段时间内使用原版GM工具发放一个装备")
    print()
    
    print("正在获取发放前快照...")
    before_snapshot = get_db_snapshot()
    print("发放前快照已获取！")
    print()
    
    print(f"请在 {WAIT_TIME} 秒内使用原版GM工具发放一个装备...")
    print("倒计时：")
    for i in range(WAIT_TIME, 0, -10):
        print(f"  剩余 {i} 秒...")
        time.sleep(10)
    
    print()
    print("正在获取发放后快照...")
    time.sleep(2)  # 等待数据库写入完成
    after_snapshot = get_db_snapshot()
    print("发放后快照已获取！")
    print()
    
    print("正在对比快照...")
    changes = compare_snapshots(before_snapshot, after_snapshot)
    
    if not changes:
        print("未发现数据库变化！")
    else:
        print(f"发现 {len(changes)} 个表有变化：")
        print()
        
        for table_name, new_items in changes.items():
            print(f"=== {table_name} (新增 {len(new_items)} 条) ===")
            for item in new_items:
                # 处理raw_entry二进制数据
                item_copy = item.copy()
                if 'raw_entry' in item_copy and item_copy['raw_entry']:
                    raw_data = item_copy['raw_entry']
                    if isinstance(raw_data, bytes):
                        item_copy['raw_entry_hex'] = raw_data.hex()
                        item_copy['raw_entry'] = f"<binary data, length={len(raw_data)}>"
                    else:
                        item_copy['raw_entry'] = str(raw_data)
                print(json.dumps(item_copy, ensure_ascii=False, default=str, indent=2))
            print()
    
    # 保存结果到文件
    output_file = os.path.join(os.path.dirname(__file__), 'gm_tool_changes.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(changes, f, ensure_ascii=False, default=str, indent=2)
    print(f"变化结果已保存到: {output_file}")

if __name__ == '__main__':
    main()
