# -*- coding: utf-8 -*-
"""查询ServiceFlags相关字段"""
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
            # 查询所有表
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            table_names = [list(t.values())[0] for t in tables]
            
            # 查找包含service、flag、premium、vip、member、black、dragon关键词的字段
            keywords = ['service', 'flag', 'premium', 'vip', 'member', 'black', 'dragon', 'grade', 'rank']
            
            print("=== 包含关键词的字段 ===")
            for table_name in table_names:
                try:
                    cursor.execute(f"DESCRIBE {table_name}")
                    columns = cursor.fetchall()
                    for col in columns:
                        field = col['Field'].lower()
                        if any(kw in field for kw in keywords):
                            print(f"  表:{table_name:40s} 字段:{col['Field']:30s} 类型:{col['Type']}")
                except:
                    pass
            print()
            
            # 查询dnf_characters表中所有字段
            print("=== dnf_characters表所有字段（查找可能与黑钻相关的）===")
            try:
                cursor.execute("DESCRIBE dnf_characters")
                columns = cursor.fetchall()
                for col in columns:
                    field = col['Field'].lower()
                    # 查找包含ack、service、flag、premium、vip、member、black、dragon、coin、cera、token、service、expire、level、grade、rank等关键词的字段
                    keywords = ['ack', 'service', 'flag', 'premium', 'vip', 'member', 'black', 'dragon', 'coin', 'cera', 'token', 'expire', 'grade', 'rank', 'level', 'stat']
                    if any(kw in field for kw in keywords):
                        print(f"  {col['Field']:30s} {col['Type']}")
            except Exception as e:
                print(f"  查询失败: {e}")
            print()
            
            # 查询第一个角色的ack_*字段
            print("=== 第一个角色的ack_*字段值 ===")
            try:
                cursor.execute("SELECT * FROM dnf_characters LIMIT 1")
                row = cursor.fetchone()
                if row:
                    for key, value in row.items():
                        if key.lower().startswith('ack_') or 'service' in key.lower() or 'flag' in key.lower() or 'premium' in key.lower():
                            print(f"  {key:30s} = {value}")
            except Exception as e:
                print(f"  查询失败: {e}")
            print()
            
            # 查询dnf_legacy_characters表结构
            print("=== dnf_legacy_characters表结构 ===")
            try:
                cursor.execute("DESCRIBE dnf_legacy_characters")
                columns = cursor.fetchall()
                for col in columns:
                    field = col['Field'].lower()
                    if any(kw in field for kw in keywords):
                        print(f"  {col['Field']:30s} {col['Type']}")
            except Exception as e:
                print(f"  查询失败: {e}")
            print()
            
            # 查询dnf_account_metadata表中所有entry_key，查找service/flag/premium相关的
            print("=== dnf_account_metadata表中service/flag/premium相关的entry_key ===")
            try:
                cursor.execute("SELECT DISTINCT entry_key FROM dnf_account_metadata ORDER BY entry_key")
                keys = cursor.fetchall()
                for k in keys:
                    key = k['entry_key'].lower()
                    if any(kw in key for kw in ['service', 'flag', 'premium', 'vip', 'member', 'black', 'dragon']):
                        print(f"  - {k['entry_key']}")
            except Exception as e:
                print(f"  查询失败: {e}")
            
        conn.close()
        print()
        print("查询完成！")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
