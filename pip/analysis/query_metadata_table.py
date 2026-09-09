# -*- coding: utf-8 -*-
"""查询dnf_account_metadata表结构和黑钻相关字段"""
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
            # 查询表结构
            print("=== dnf_account_metadata表结构 ===")
            cursor.execute("DESCRIBE dnf_account_metadata")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  {col['Field']:20s} {col['Type']:20s} Null:{col['Null']:5s} Key:{col['Key']:5s} Default:{col['Default']}")
            print()
            
            # 查询主键和索引
            print("=== dnf_account_metadata表索引 ===")
            cursor.execute("SHOW INDEX FROM dnf_account_metadata")
            indexes = cursor.fetchall()
            for idx in indexes:
                print(f"  索引名:{idx['Key_name']:20s} 列:{idx['Column_name']:20s} 唯一:{idx['Non_unique']==0}")
            print()
            
            # 查询第一个账号的所有premium_expire字段
            print("=== 第一个账号的premium_expire字段 ===")
            cursor.execute("SELECT account_id FROM dnf_accounts LIMIT 1")
            account = cursor.fetchone()
            if account:
                account_id = account['account_id']
                print(f"账号ID: {account_id}")
                print()
                cursor.execute("SELECT entry_key, entry_value FROM dnf_account_metadata WHERE account_id = %s AND entry_key LIKE 'premium_expire_%%' ORDER BY entry_key", (account_id,))
                metadatas = cursor.fetchall()
                for m in metadatas:
                    key = m['entry_key']
                    value = int(m['entry_value']) if m['entry_value'] else 0
                    from datetime import datetime
                    time_str = datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S') if value > 0 else "0"
                    print(f"  {key:30s} = {value:12d} ({time_str})")
            print()
            
            # 测试INSERT ... ON DUPLICATE KEY UPDATE
            print("=== 测试INSERT ... ON DUPLICATE KEY UPDATE ===")
            try:
                test_key = "test_black_dragon_key"
                test_value = "1234567890"
                query = """
                    INSERT INTO dnf_account_metadata (account_id, entry_key, entry_value)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE entry_value = %s
                """
                cursor.execute(query, (account_id, test_key, test_value, test_value))
                conn.commit()
                print("INSERT ... ON DUPLICATE KEY UPDATE 测试成功！")
                
                # 查询测试数据
                cursor.execute("SELECT entry_value FROM dnf_account_metadata WHERE account_id = %s AND entry_key = %s", (account_id, test_key))
                result = cursor.fetchone()
                print(f"查询结果: {result}")
                
                # 删除测试数据
                cursor.execute("DELETE FROM dnf_account_metadata WHERE account_id = %s AND entry_key = %s", (account_id, test_key))
                conn.commit()
                print("测试数据已删除")
            except Exception as e:
                print(f"INSERT ... ON DUPLICATE KEY UPDATE 测试失败: {e}")
                import traceback
                traceback.print_exc()
            
        conn.close()
        print()
        print("查询完成！")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
