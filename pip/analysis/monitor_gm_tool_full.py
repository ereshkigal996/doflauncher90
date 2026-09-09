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

WAIT_TIME = 60  # 等待时间（秒）

def get_all_tables():
    """获取数据库中所有表名"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables

def get_table_count(table_name):
    """获取表的记录数"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return -1

def get_table_snapshot(table_name, limit=100):
    """获取表的快照（最近的记录）"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        # 尝试获取表的主键或第一个字段作为排序依据
        cursor.execute(f"DESCRIBE `{table_name}`")
        columns = cursor.fetchall()
        first_column = columns[0][0] if columns else None
        
        if first_column:
            cursor.execute(f"SELECT * FROM `{table_name}` ORDER BY `{first_column}` DESC LIMIT {limit}")
        else:
            cursor.execute(f"SELECT * FROM `{table_name}` LIMIT {limit}")
        
        data = cursor.fetchall()
        conn.close()
        return data
    except Exception as e:
        return []

def main():
    print("=== 原版GM工具全表监控脚本 ===")
    print()
    
    # 获取所有表
    print("正在获取数据库中所有表...")
    all_tables = get_all_tables()
    print(f"共发现 {len(all_tables)} 个表")
    print()
    
    # 获取发放前的记录数
    print("正在获取发放前的表记录数...")
    before_counts = {}
    for table in all_tables:
        count = get_table_count(table)
        before_counts[table] = count
    print("发放前记录数已获取！")
    print()
    
    print(f"请在 {WAIT_TIME} 秒内使用原版GM工具发放一个装备...")
    print("倒计时：")
    for i in range(WAIT_TIME, 0, -10):
        print(f"  剩余 {i} 秒...")
        time.sleep(10)
    
    print()
    print("正在获取发放后的表记录数...")
    time.sleep(2)
    after_counts = {}
    for table in all_tables:
        count = get_table_count(table)
        after_counts[table] = count
    print("发放后记录数已获取！")
    print()
    
    # 对比记录数变化
    print("=== 记录数变化的表 ===")
    changed_tables = []
    for table in all_tables:
        before = before_counts.get(table, 0)
        after = after_counts.get(table, 0)
        if before != after:
            print(f"  {table}: {before} -> {after} (变化: {after - before})")
            changed_tables.append(table)
    
    if not changed_tables:
        print("  未发现记录数变化！")
    print()
    
    # 获取变化表的详细数据
    if changed_tables:
        print("=== 获取变化表的详细数据 ===")
        changes = {}
        for table in changed_tables:
            print(f"正在获取 {table} 的数据...")
            before_data = get_table_snapshot(table, limit=50)
            after_data = get_table_snapshot(table, limit=50)
            
            # 简单对比，找出新增的记录
            before_ids = set()
            for item in before_data:
                before_ids.add(json.dumps(item, sort_keys=True, default=str))
            
            new_items = []
            for item in after_data:
                item_str = json.dumps(item, sort_keys=True, default=str)
                if item_str not in before_ids:
                    # 处理二进制数据
                    item_copy = item.copy()
                    for key, value in item_copy.items():
                        if isinstance(value, bytes):
                            item_copy[key] = f"<binary data, length={len(value)}, hex={value.hex()[:100]}...>"
                    new_items.append(item_copy)
            
            if new_items:
                changes[table] = new_items
                print(f"  {table}: 发现 {len(new_items)} 条新记录")
        
        print()
        print("=== 详细变化数据 ===")
        for table, items in changes.items():
            print(f"\n--- {table} ---")
            for item in items:
                print(json.dumps(item, ensure_ascii=False, default=str, indent=2))
        
        # 保存结果
        output_file = os.path.join(os.path.dirname(__file__), 'gm_tool_full_changes.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(changes, f, ensure_ascii=False, default=str, indent=2)
        print(f"\n详细变化结果已保存到: {output_file}")

if __name__ == '__main__':
    main()
