# -*- coding: utf-8 -*-
"""查询ack_premium_blob和其他可能与黑钻相关的字段"""
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
            # 查询dnf_legacy_character_init_flags表结构
            print("=== dnf_legacy_character_init_flags表结构 ===")
            try:
                cursor.execute("DESCRIBE dnf_legacy_character_init_flags")
                columns = cursor.fetchall()
                for col in columns:
                    print(f"  {col['Field']:30s} {col['Type']}")
            except Exception as e:
                print(f"  查询失败: {e}")
            print()
            
            # 查询第一个角色的ack_premium_blob
            print("=== 第一个角色的ack_premium_blob ===")
            try:
                cursor.execute("SELECT character_id, ack_premium_blob FROM dnf_legacy_character_init_flags LIMIT 1")
                row = cursor.fetchone()
                if row:
                    print(f"  character_id: {row['character_id']}")
                    blob = row['ack_premium_blob']
                    if blob:
                        print(f"  ack_premium_blob长度: {len(blob)} 字节")
                        print(f"  ack_premium_blob前100字节(hex): {blob[:100].hex()}")
                        # 尝试解析为文本
                        try:
                            text = blob.decode('utf-8', errors='replace')
                            print(f"  ack_premium_blob文本: {text[:200]}")
                        except:
                            pass
                    else:
                        print(f"  ack_premium_blob: NULL")
            except Exception as e:
                print(f"  查询失败: {e}")
                import traceback
                traceback.print_exc()
            print()
            
            # 查询所有包含premium的表
            print("=== 所有包含premium的表 ===")
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            table_names = [list(t.values())[0] for t in tables]
            premium_tables = [t for t in table_names if 'premium' in t.lower() or 'vip' in t.lower() or 'member' in t.lower()]
            for t in premium_tables:
                print(f"  - {t}")
            print()
            
            # 查询dnf_characters表中所有字段，看看有没有黑钻相关的
            print("=== dnf_characters表中可能与黑钻相关的字段 ===")
            try:
                cursor.execute("DESCRIBE dnf_characters")
                columns = cursor.fetchall()
                keywords = ['black', 'dragon', 'vip', 'member', 'premium', 'coin', 'cera', 'token']
                for col in columns:
                    field = col['Field'].lower()
                    if any(kw in field for kw in keywords):
                        print(f"  {col['Field']:30s} {col['Type']}")
            except Exception as e:
                print(f"  查询失败: {e}")
            print()
            
            # 查询第一个角色的这些字段的值
            print("=== 第一个角色的相关字段值 ===")
            try:
                cursor.execute("SELECT character_id, name, cera, coin, black_count, premium_crystal_selection, is_premium_pc_room FROM dnf_characters LIMIT 1")
                row = cursor.fetchone()
                if row:
                    for key, value in row.items():
                        print(f"  {key:30s} = {value}")
            except Exception as e:
                print(f"  查询失败: {e}")
            print()
            
            # 查询所有表，看看有没有black_dragon相关的表
            print("=== 所有包含black或dragon的表 ===")
            black_tables = [t for t in table_names if 'black' in t.lower() or 'dragon' in t.lower()]
            for t in black_tables:
                print(f"  - {t}")
            print()
            
            # 查询dnf_account_metadata表中所有不同的entry_key
            print("=== dnf_account_metadata表中所有不同的entry_key ===")
            try:
                cursor.execute("SELECT DISTINCT entry_key FROM dnf_account_metadata ORDER BY entry_key")
                keys = cursor.fetchall()
                for k in keys:
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
