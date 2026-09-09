# -*- coding: utf-8 -*-
"""查询dnf_account_metadata表中所有的entry_key，找到黑钻相关字段"""
import pymysql

DEFAULT_DB_PASSWORD = "db_ed372bfa36051308258d2a75f431e91b"

def main():
    try:
        conn = pymysql.connect(
            host="127.0.0.1",
            port=13306,
            user="root",
            password=DEFAULT_DB_PASSWORD,
            database="dnf_local",
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print("数据库连接成功！")
        print()
        
        with conn.cursor() as cursor:
            # 查询dnf_account_metadata表中所有的entry_key
            print("=== dnf_account_metadata表中所有的entry_key ===")
            cursor.execute("SELECT DISTINCT entry_key FROM dnf_account_metadata ORDER BY entry_key")
            keys = cursor.fetchall()
            for k in keys:
                key = k['entry_key']
                # 标记可能相关的字段
                relevant = ''
                if any(kw in key.lower() for kw in ['cera', 'point', 'vip', 'black', 'dragon', 'member', 'level', 'expire', 'end', 'time', 'service', 'premium']):
                    relevant = '  <-- 可能相关!'
                print(f"  {key}{relevant}")
            print()
            
            # 查询第一个账号的所有metadata
            print("=== 第一个账号的所有metadata ===")
            cursor.execute("SELECT account_id FROM dnf_accounts LIMIT 1")
            account = cursor.fetchone()
            if account:
                account_id = account['account_id']
                print(f"账号ID: {account_id}")
                print()
                cursor.execute("SELECT entry_key, entry_value FROM dnf_account_metadata WHERE account_id = %s ORDER BY entry_key", (account_id,))
                metadatas = cursor.fetchall()
                for m in metadatas:
                    key = m['entry_key']
                    value = m['entry_value']
                    # 标记可能相关的字段
                    relevant = ''
                    if any(kw in key.lower() for kw in ['cera', 'point', 'vip', 'black', 'dragon', 'member', 'level', 'expire', 'end', 'time', 'service', 'premium']):
                        relevant = '  <-- 可能相关!'
                    print(f"  {key:40s} = {value}{relevant}")
            
            print()
            
            # 查找包含black/dragon/vip/member的表
            print("=== 查找包含black/dragon/vip/member的表 ===")
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            table_names = [list(t.values())[0] for t in tables]
            for t in table_names:
                if any(kw in t.lower() for kw in ['black', 'dragon', 'vip', 'member', 'service', 'premium']):
                    print(f"  - {t}")
            print()
            
            # 查找dnf_characters表的结构
            print("=== dnf_characters表结构 ===")
            cursor.execute("DESCRIBE dnf_characters")
            columns = cursor.fetchall()
            for col in columns:
                field = col.get('Field', '')
                type_ = col.get('Type', '')
                relevant = ''
                if any(kw in field.lower() for kw in ['gold', 'cera', 'vip', 'black', 'dragon', 'member', 'level', 'expire']):
                    relevant = '  <-- 可能相关!'
                print(f"  {field:30s} {type_:20s} {relevant}")
            
        conn.close()
        print()
        print("查询完成！")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
