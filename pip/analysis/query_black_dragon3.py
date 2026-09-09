# -*- coding: utf-8 -*-
"""查询ack_premium_blob字段内容，分析黑钻生效机制"""
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
            # 查询所有角色的ack_premium_blob字段
            print("=== 所有角色的ack_premium_blob字段 ===")
            try:
                cursor.execute("SELECT character_id, ack_premium_blob FROM dnf_legacy_character_init_flags")
                rows = cursor.fetchall()
                print(f"共 {len(rows)} 个角色")
                print()
                for row in rows:
                    char_id = row['character_id']
                    blob = row['ack_premium_blob']
                    if blob:
                        print(f"角色ID: {char_id}, ack_premium_blob长度: {len(blob)} 字节")
                        print(f"  hex: {blob[:200].hex()}")
                        # 尝试解析为文本
                        try:
                            text = blob.decode('utf-8', errors='replace')
                            print(f"  文本: {text[:200]}")
                        except:
                            pass
                        print()
                    else:
                        print(f"角色ID: {char_id}, ack_premium_blob: NULL")
                print()
            except Exception as e:
                print(f"查询失败: {e}")
                import traceback
                traceback.print_exc()
                print()
            
            # 查询所有角色的premium_expire字段
            print("=== 所有账号的premium_expire字段 ===")
            try:
                cursor.execute("SELECT account_id, entry_key, entry_value FROM dnf_account_metadata WHERE entry_key LIKE 'premium_expire_%%' ORDER BY account_id, entry_key")
                rows = cursor.fetchall()
                print(f"共 {len(rows)} 条记录")
                print()
                current_account = None
                for row in rows:
                    account_id = row['account_id']
                    if account_id != current_account:
                        print(f"账号: {account_id}")
                        current_account = account_id
                    from datetime import datetime
                    try:
                        ts = int(row['entry_value'])
                        time_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        time_str = row['entry_value']
                    print(f"  {row['entry_key']:30s} = {time_str}")
                print()
            except Exception as e:
                print(f"查询失败: {e}")
                import traceback
                traceback.print_exc()
                print()
            
            # 查询dnf_characters表中所有字段，看看有没有其他可能与黑钻相关的字段
            print("=== dnf_characters表中所有字段（查找可能与黑钻相关的）===")
            try:
                cursor.execute("DESCRIBE dnf_characters")
                columns = cursor.fetchall()
                # 查找包含ack、premium、vip、member、black、dragon、coin、cera、token、service等关键词的字段
                keywords = ['ack', 'premium', 'vip', 'member', 'black', 'dragon', 'coin', 'cera', 'token', 'service', 'expire', 'level', 'grade', 'rank']
                for col in columns:
                    field = col['Field'].lower()
                    if any(kw in field for kw in keywords):
                        print(f"  {col['Field']:30s} {col['Type']}")
            except Exception as e:
                print(f"查询失败: {e}")
            print()
            
            # 查询第一个角色的所有字段值（只显示可能相关的）
            print("=== 第一个角色的相关字段值 ===")
            try:
                cursor.execute("SELECT * FROM dnf_characters LIMIT 1")
                row = cursor.fetchone()
                if row:
                    keywords = ['ack', 'premium', 'vip', 'member', 'black', 'dragon', 'coin', 'cera', 'token', 'service', 'expire', 'level', 'grade', 'rank']
                    for key, value in row.items():
                        if any(kw in key.lower() for kw in keywords):
                            print(f"  {key:30s} = {value}")
            except Exception as e:
                print(f"查询失败: {e}")
            
        conn.close()
        print()
        print("查询完成！")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
