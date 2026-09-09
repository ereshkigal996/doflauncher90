# -*- coding: utf-8 -*-
"""查询数据库表结构，找到点券和黑钻相关字段"""
import pymysql
import sys

# 默认数据库密码
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
            print(f"数据库共有 {len(table_names)} 张表")
            print()
            
            # 查找包含账号、点券、黑钻、vip相关的表
            keyword_tables = [t for t in table_names if any(k in t.lower() for k in ['account', 'user', 'member', 'cera', 'point', 'vip', 'black', 'dragon', 'member'])]
            print("=== 可能包含账号/点券/黑钻信息的表 ===")
            for t in keyword_tables:
                print(f"  - {t}")
            print()
            
            # 查询这些表的结构
            for table_name in keyword_tables[:10]:  # 只查前10个
                print(f"=== 表结构: {table_name} ===")
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
                for col in columns:
                    field = col.get('Field', '')
                    type_ = col.get('Type', '')
                    comment = col.get('Comment', '')
                    # 标记可能相关的字段
                    relevant = ''
                    if any(k in field.lower() for k in ['cera', 'point', 'vip', 'black', 'dragon', 'member', 'level', 'expire', 'end', 'time']):
                        relevant = '  <-- 可能相关!'
                    print(f"  {field:30s} {type_:20s} {comment} {relevant}")
                print()
                
                # 查询前3条数据
                try:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                    rows = cursor.fetchall()
                    if rows:
                        print(f"  前3条数据:")
                        for i, row in enumerate(rows):
                            print(f"    [{i+1}] {dict(row)}")
                        print()
                except Exception as e:
                    print(f"  查询数据失败: {e}")
                    print()
            
            # 特别查找metadata表
            metadata_tables = [t for t in table_names if 'metadata' in t.lower()]
            if metadata_tables:
                print("=== metadata相关表 ===")
                for t in metadata_tables:
                    print(f"  - {t}")
                print()
                
                for table_name in metadata_tables:
                    print(f"=== 表结构: {table_name} ===")
                    cursor.execute(f"DESCRIBE {table_name}")
                    columns = cursor.fetchall()
                    for col in columns:
                        field = col.get('Field', '')
                        type_ = col.get('Type', '')
                        print(f"  {field:30s} {type_}")
                    print()
                    
                    # 查询前5条数据
                    try:
                        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                        rows = cursor.fetchall()
                        if rows:
                            print(f"  前5条数据:")
                            for i, row in enumerate(rows):
                                print(f"    [{i+1}] {dict(row)}")
                            print()
                    except Exception as e:
                        print(f"  查询数据失败: {e}")
                        print()
        
        conn.close()
        print("查询完成！")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
