# -*- coding: utf-8 -*-
"""查询数据库中所有与黑钻/vip/会员相关的字段"""
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
            
            # 搜索包含black/dragon/vip/member/premium/cera关键词的字段
            keywords = ['black', 'dragon', 'vip', 'member', 'premium', 'cera', 'coin', 'token']
            
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
            
            # 查询第一个账号的所有metadata，看看有没有其他相关字段
            print("=== 第一个账号的所有metadata（按关键词过滤）===")
            cursor.execute("SELECT account_id FROM dnf_accounts LIMIT 1")
            account = cursor.fetchone()
            if account:
                account_id = account['account_id']
                print(f"账号ID: {account_id}")
                print()
                cursor.execute("SELECT entry_key, entry_value FROM dnf_account_metadata WHERE account_id = %s ORDER BY entry_key", (account_id,))
                metadatas = cursor.fetchall()
                for m in metadatas:
                    key = m['entry_key'].lower()
                    if any(kw in key for kw in keywords):
                        value = m['entry_value']
                        # 如果是时间戳，转换为日期
                        try:
                            from datetime import datetime
                            ts = int(value)
                            if ts > 1000000000:  # 看起来像时间戳
                                time_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                                value = f"{value} ({time_str})"
                        except:
                            pass
                        print(f"  {m['entry_key']:40s} = {value}")
            print()
            
            # 查询dnf_legacy_accounts表的所有字段
            print("=== dnf_legacy_accounts表所有字段 ===")
            try:
                cursor.execute("DESCRIBE dnf_legacy_accounts")
                columns = cursor.fetchall()
                for col in columns:
                    print(f"  {col['Field']:30s} {col['Type']}")
            except Exception as e:
                print(f"  查询失败: {e}")
            print()
            
            # 查询第一个legacy账号的数据
            print("=== 第一个legacy账号数据 ===")
            try:
                cursor.execute("SELECT * FROM dnf_legacy_accounts LIMIT 1")
                row = cursor.fetchone()
                if row:
                    for key, value in row.items():
                        print(f"  {key:30s} = {value}")
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
