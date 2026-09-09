# -*- coding: utf-8 -*-
"""测试premium_expire_1000字段是否与黑钻有关"""
import pymysql
import json
import time
import urllib.request
import subprocess

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

# 测试账号和角色
TEST_ACCOUNT_ID = "dnf:43ca6920ecea925361055c8e9463fd15"
TEST_CHARACTER_ID = "1"

def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

def get_premium_expire_values():
    """获取所有premium_expire_*字段的值"""
    conn = get_db_connection()
    values = {}
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT entry_key, entry_value FROM dnf_account_metadata WHERE account_id = %s AND entry_key LIKE 'premium_expire_%%'", (TEST_ACCOUNT_ID,))
            records = cursor.fetchall()
            for record in records:
                values[record['entry_key']] = record['entry_value']
    finally:
        conn.close()
    return values

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
                        pid = parts[-1] if len(parts) >= 5 else ''
                        if pid:
                            result2 = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV'], capture_output=True, text=True)
                            if 'DNF90GMTool' in result2.stdout:
                                return port
    except:
        pass
    return None

def main():
    print("=== 测试premium_expire_1000字段是否与黑钻有关 ===")
    print()
    
    # 1. 启动原版GM工具
    print("1. 启动原版GM工具...")
    proc = subprocess.Popen([GM_TOOL_PATH], cwd=GM_TOOL_WORKDIR)
    print(f"   进程ID: {proc.pid}")
    time.sleep(8)
    
    gm_tool_port = get_gm_tool_port()
    if not gm_tool_port:
        print("   错误: 无法获取原版GM工具的监听端口")
        proc.terminate()
        return
    
    gm_tool_api = f"http://127.0.0.1:{gm_tool_port}"
    print(f"   原版GM工具API地址: {gm_tool_api}")
    print()
    
    # 2. 记录调用前所有premium_expire_*字段的值
    print("2. 记录调用前所有premium_expire_*字段的值...")
    before_values = get_premium_expire_values()
    for key, value in sorted(before_values.items()):
        print(f"   {key}: {value}")
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
            print(f"   响应: {response_text}")
            
            # 解析响应中的expires_at
            response_data = json.loads(response_text)
            if response_data.get('ok'):
                expires_at = response_data.get('data', {}).get('expires_at')
                print(f"   API返回的expires_at: {expires_at}")
    except Exception as e:
        print(f"   调用失败: {str(e)}")
        proc.terminate()
        return
    print()
    
    # 等待数据库操作完成
    print("4. 等待数据库操作完成...")
    time.sleep(3)
    print()
    
    # 5. 记录调用后所有premium_expire_*字段的值
    print("5. 记录调用后所有premium_expire_*字段的值...")
    after_values = get_premium_expire_values()
    for key, value in sorted(after_values.items()):
        print(f"   {key}: {value}")
    print()
    
    # 6. 比较差异
    print("6. 比较差异...")
    all_keys = set(list(before_values.keys()) + list(after_values.keys()))
    changes = []
    for key in sorted(all_keys):
        before = before_values.get(key, '不存在')
        after = after_values.get(key, '不存在')
        if before != after:
            changes.append({
                'key': key,
                'before': before,
                'after': after
            })
            print(f"   {key}: {before} -> {after}")
    
    if not changes:
        print("   未发现变化！")
    print()
    
    # 7. 关闭原版GM工具
    print("7. 关闭原版GM工具...")
    proc.terminate()
    print("   已关闭")
    print()
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    main()
