# -*- coding: utf-8 -*-
"""启动原版GM工具并监控黑钻开启时的数据库变化"""
import pymysql
import json
import time
import urllib.request
import subprocess
import os
import re

# 数据库配置
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 13306,
    "user": "root",
    "password": "db_ed372bfa36051308258d2a75f431e91b",
    "database": "dnf_local",
    "charset": "utf8mb4",
}

# 原版GM工具路径
GM_TOOL_PATH = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\bin\DNF90GMTool.exe"
GM_TOOL_WORKDIR = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\bin"

# 测试角色ID
TEST_CHARACTER_ID = "1"

def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

def snapshot_database():
    """快照数据库中所有表的数据"""
    conn = get_db_connection()
    snapshot = {}
    
    try:
        with conn.cursor() as cursor:
            # 获取所有表名
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            table_names = [list(t.values())[0] for t in tables]
            
            for table_name in table_names:
                try:
                    # 获取表数据
                    cursor.execute(f"SELECT * FROM {table_name}")
                    rows = cursor.fetchall()
                    snapshot[table_name] = rows
                except Exception as e:
                    snapshot[table_name] = f"Error: {str(e)}"
    finally:
        conn.close()
    
    return snapshot

def compare_snapshots(before, after):
    """比较两个数据库快照，找出变化"""
    changes = {}
    
    all_tables = set(list(before.keys()) + list(after.keys()))
    
    for table_name in all_tables:
        before_data = before.get(table_name, [])
        after_data = after.get(table_name, [])
        
        if before_data == after_data:
            continue
        
        table_changes = {
            "added": [],
            "modified": [],
            "deleted": []
        }
        
        if isinstance(before_data, list) and isinstance(after_data, list):
            # 尝试找到主键字段
            primary_key = None
            if len(before_data) > 0:
                for key in before_data[0].keys():
                    if 'id' in key.lower() or 'key' in key.lower():
                        primary_key = key
                        break
            
            if not primary_key and len(after_data) > 0:
                for key in after_data[0].keys():
                    if 'id' in key.lower() or 'key' in key.lower():
                        primary_key = key
                        break
            
            if primary_key:
                # 使用主键比较
                before_ids = {}
                after_ids = {}
                
                for row in before_data:
                    key_val = str(row.get(primary_key, ''))
                    before_ids[key_val] = row
                
                for row in after_data:
                    key_val = str(row.get(primary_key, ''))
                    after_ids[key_val] = row
                
                # 新增
                for key_val in after_ids:
                    if key_val not in before_ids:
                        table_changes["added"].append(after_ids[key_val])
                
                # 删除
                for key_val in before_ids:
                    if key_val not in after_ids:
                        table_changes["deleted"].append(before_ids[key_val])
                
                # 修改
                for key_val in after_ids:
                    if key_val in before_ids and before_ids[key_val] != after_ids[key_val]:
                        modified_fields = {}
                        for field in after_ids[key_val]:
                            if before_ids[key_val].get(field) != after_ids[key_val].get(field):
                                modified_fields[field] = {
                                    "before": before_ids[key_val].get(field),
                                    "after": after_ids[key_val].get(field)
                                }
                        table_changes["modified"].append({
                            "primary_key": key_val,
                            "modified_fields": modified_fields
                        })
            else:
                # 没有主键，比较行数
                if len(before_data) != len(after_data):
                    table_changes["row_count_change"] = {
                        "before": len(before_data),
                        "after": len(after_data)
                    }
        
        if table_changes["added"] or table_changes["modified"] or table_changes["deleted"] or table_changes.get("row_count_change"):
            changes[table_name] = table_changes
    
    return changes

def get_gm_tool_port():
    """获取原版GM工具的监听端口"""
    try:
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'LISTENING' in line and '127.0.0.1' in line:
                parts = line.split()
                if len(parts) >= 2:
                    local_addr = parts[1]
                    if ':' in local_addr:
                        port = local_addr.split(':')[-1]
                        # 检查这个端口是否属于DNF90GMTool进程
                        pid = parts[-1] if len(parts) >= 5 else ''
                        if pid:
                            result2 = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV'], capture_output=True, text=True)
                            if 'DNF90GMTool' in result2.stdout:
                                return port
    except:
        pass
    return None

def main():
    print("=== 启动原版GM工具并监控黑钻开启时的数据库变化 ===")
    print()
    
    # 1. 启动原版GM工具
    print("1. 启动原版GM工具...")
    proc = subprocess.Popen([GM_TOOL_PATH], cwd=GM_TOOL_WORKDIR)
    print(f"   进程ID: {proc.pid}")
    
    # 等待启动
    print("   等待启动...")
    time.sleep(8)
    
    # 获取监听端口
    gm_tool_port = get_gm_tool_port()
    if not gm_tool_port:
        print("   错误: 无法获取原版GM工具的监听端口")
        proc.terminate()
        return
    
    gm_tool_api = f"http://127.0.0.1:{gm_tool_port}"
    print(f"   原版GM工具API地址: {gm_tool_api}")
    print()
    
    # 2. 调用前快照
    print("2. 记录调用前数据库快照...")
    before_snapshot = snapshot_database()
    print(f"   已快照 {len(before_snapshot)} 个表")
    print()
    
    # 3. 调用黑钻API
    print("3. 调用原版GM工具的黑钻API...")
    try:
        api_url = f"{gm_tool_api}/api/character/black-diamond"
        data = json.dumps({"characterId": TEST_CHARACTER_ID, "days": 30}).encode('utf-8')
        
        req = urllib.request.Request(
            api_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            response_text = response.read().decode('utf-8', errors='replace')
            print(f"   状态码: {status}")
            print(f"   响应: {response_text[:500]}")
    except Exception as e:
        print(f"   调用失败: {str(e)}")
        proc.terminate()
        return
    print()
    
    # 等待数据库操作完成
    print("4. 等待数据库操作完成...")
    time.sleep(3)
    print()
    
    # 5. 调用后快照
    print("5. 记录调用后数据库快照...")
    after_snapshot = snapshot_database()
    print(f"   已快照 {len(after_snapshot)} 个表")
    print()
    
    # 6. 比较差异
    print("6. 比较数据库变化...")
    changes = compare_snapshots(before_snapshot, after_snapshot)
    
    if not changes:
        print("   未发现数据库变化！")
    else:
        print(f"   发现 {len(changes)} 个表有变化：")
        print()
        for table_name, table_changes in changes.items():
            print(f"   表: {table_name}")
            if table_changes.get("added"):
                print(f"     新增记录: {len(table_changes['added'])} 条")
                for row in table_changes['added'][:3]:
                    print(f"       {json.dumps(row, ensure_ascii=False, default=str)[:200]}")
            if table_changes.get("modified"):
                print(f"     修改记录: {len(table_changes['modified'])} 条")
                for mod in table_changes['modified'][:3]:
                    print(f"       主键: {mod['primary_key']}")
                    for field, change in mod['modified_fields'].items():
                        print(f"         {field}: {change['before']} -> {change['after']}")
            if table_changes.get("deleted"):
                print(f"     删除记录: {len(table_changes['deleted'])} 条")
            if table_changes.get("row_count_change"):
                print(f"     行数变化: {table_changes['row_count_change']['before']} -> {table_changes['row_count_change']['after']}")
            print()
    
    # 7. 保存变化结果到文件
    print("7. 保存变化结果到文件...")
    with open(r'C:\Users\56518\Downloads\doubao_work\pip\black_diamond_db_changes.json', 'w', encoding='utf-8') as f:
        json.dump(changes, f, ensure_ascii=False, indent=2, default=str)
    print("   已保存到 black_diamond_db_changes.json")
    print()
    
    # 8. 关闭原版GM工具
    print("8. 关闭原版GM工具...")
    proc.terminate()
    print("   已关闭")
    print()
    
    print("=== 分析完成 ===")

if __name__ == "__main__":
    main()
