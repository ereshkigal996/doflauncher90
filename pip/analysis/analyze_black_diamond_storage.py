# -*- coding: utf-8 -*-
"""深入分析数据库结构，找出黑钻的正确存储位置"""
import pymysql

# 数据库配置
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 13306,
    "user": "root",
    "password": "db_ed372bfa36051308258d2a75f431e91b",
    "database": "dnf_local",
    "charset": "utf8mb4",
}

def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

def main():
    print("=== 深入分析数据库结构，找出黑钻的正确存储位置 ===")
    print()
    
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cursor:
            # 1. 获取所有表名
            print("1. 获取所有表名...")
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            table_names = [list(t.values())[0] for t in tables]
            print(f"   共 {len(table_names)} 个表")
            print()
            
            # 2. 查找包含premium、black、diamond、vip等关键词的表
            print("2. 查找包含黑钻相关关键词的表...")
            black_diamond_keywords = ['premium', 'black', 'diamond', 'vip', 'member', 'entitlement']
            related_tables = []
            for table_name in table_names:
                table_name_lower = table_name.lower()
                for keyword in black_diamond_keywords:
                    if keyword in table_name_lower:
                        related_tables.append(table_name)
                        break
            
            if related_tables:
                print(f"   找到 {len(related_tables)} 个相关表:")
                for table_name in related_tables:
                    print(f"     - {table_name}")
            else:
                print("   未找到相关表")
            print()
            
            # 3. 查找所有表中包含premium、black、diamond、vip等关键词的字段
            print("3. 查找所有表中包含黑钻相关关键词的字段...")
            related_fields = []
            for table_name in table_names:
                try:
                    cursor.execute(f"DESCRIBE {table_name}")
                    fields = cursor.fetchall()
                    for field in fields:
                        field_name = field['Field'].lower()
                        for keyword in black_diamond_keywords:
                            if keyword in field_name:
                                related_fields.append({
                                    'table': table_name,
                                    'field': field['Field'],
                                    'type': field['Type']
                                })
                                break
                except:
                    pass
            
            if related_fields:
                print(f"   找到 {len(related_fields)} 个相关字段:")
                for rf in related_fields:
                    print(f"     表: {rf['table']}, 字段: {rf['field']}, 类型: {rf['type']}")
            else:
                print("   未找到相关字段")
            print()
            
            # 4. 查询dnf_account_metadata表中所有与测试账号相关的记录
            print("4. 查询dnf_account_metadata表中所有与测试账号相关的记录...")
            test_account_id = "dnf:43ca6920ecea925361055c8e9463fd15"
            try:
                cursor.execute("SELECT * FROM dnf_account_metadata WHERE account_id = %s", (test_account_id,))
                records = cursor.fetchall()
                print(f"   找到 {len(records)} 条记录:")
                for record in records:
                    entry_key = record.get('entry_key', '')
                    entry_value = record.get('entry_value', '')
                    # 只显示与黑钻相关的记录
                    if any(keyword in entry_key.lower() for keyword in black_diamond_keywords + ['expire', '580', '581', '582', '583', '584', '585', '586', '587']):
                        print(f"     {entry_key}: {entry_value}")
            except Exception as e:
                print(f"   查询失败: {str(e)}")
            print()
            
            # 5. 查询dnf_accounts表中测试账号的所有字段
            print("5. 查询dnf_accounts表中测试账号的所有字段...")
            try:
                cursor.execute("SELECT * FROM dnf_accounts WHERE account_id = %s", (test_account_id,))
                records = cursor.fetchall()
                if records:
                    record = records[0]
                    print(f"   找到 {len(record)} 个字段:")
                    for key, value in record.items():
                        # 只显示与黑钻相关的字段
                        if any(keyword in key.lower() for keyword in black_diamond_keywords + ['expire', 'premium', 'vip']):
                            print(f"     {key}: {value}")
                else:
                    print("   未找到记录")
            except Exception as e:
                print(f"   查询失败: {str(e)}")
            print()
            
            # 6. 查询dnf_characters表中测试角色的所有字段
            print("6. 查询dnf_characters表中测试角色的所有字段...")
            test_character_id = "1"
            try:
                cursor.execute("SELECT * FROM dnf_characters WHERE character_id = %s", (test_character_id,))
                records = cursor.fetchall()
                if records:
                    record = records[0]
                    print(f"   找到 {len(record)} 个字段:")
                    for key, value in record.items():
                        # 只显示与黑钻相关的字段
                        if any(keyword in key.lower() for keyword in black_diamond_keywords + ['expire', 'premium', 'vip']):
                            print(f"     {key}: {value}")
                else:
                    print("   未找到记录")
            except Exception as e:
                print(f"   查询失败: {str(e)}")
            print()
            
            # 7. 查找所有包含expire关键词的字段
            print("7. 查找所有包含expire关键词的字段...")
            expire_fields = []
            for table_name in table_names:
                try:
                    cursor.execute(f"DESCRIBE {table_name}")
                    fields = cursor.fetchall()
                    for field in fields:
                        if 'expire' in field['Field'].lower():
                            expire_fields.append({
                                'table': table_name,
                                'field': field['Field'],
                                'type': field['Type']
                            })
                except:
                    pass
            
            if expire_fields:
                print(f"   找到 {len(expire_fields)} 个相关字段:")
                for ef in expire_fields:
                    print(f"     表: {ef['table']}, 字段: {ef['field']}, 类型: {ef['type']}")
            else:
                print("   未找到相关字段")
            print()
            
            # 8. 查询dnf_account_metadata表中所有不同的entry_key
            print("8. 查询dnf_account_metadata表中所有不同的entry_key...")
            try:
                cursor.execute("SELECT DISTINCT entry_key FROM dnf_account_metadata ORDER BY entry_key")
                records = cursor.fetchall()
                print(f"   找到 {len(records)} 个不同的entry_key:")
                for record in records:
                    entry_key = record['entry_key']
                    # 只显示与黑钻相关的entry_key
                    if any(keyword in entry_key.lower() for keyword in black_diamond_keywords + ['expire', '580', '581', '582', '583', '584', '585', '586', '587', 'premium']):
                        print(f"     {entry_key}")
            except Exception as e:
                print(f"   查询失败: {str(e)}")
            print()
            
    finally:
        conn.close()
    
    print("=== 分析完成 ===")

if __name__ == "__main__":
    main()
