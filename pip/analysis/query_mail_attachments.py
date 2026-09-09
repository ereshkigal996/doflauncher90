import pymysql
import json

# 连接数据库
conn = pymysql.connect(
    host='127.0.0.1',
    port=13306,
    user='root',
    password='db_ed372bfa36051308258d2a75f431e91b',
    database='dnf_local',
    charset='utf8mb4'
)
cursor = conn.cursor(pymysql.cursors.DictCursor)

# 查询邮件附件表结构
print('=== dnf_mail_attachments 表结构 ===')
cursor.execute('DESCRIBE dnf_mail_attachments')
for row in cursor.fetchall():
    print(row)

print()
print('=== 查询最近的邮件附件（前5条）===')
cursor.execute('SELECT * FROM dnf_mail_attachments ORDER BY character_id DESC LIMIT 5')
for row in cursor.fetchall():
    print(json.dumps(row, ensure_ascii=False, default=str))
    print()

# 查询是否有邮件附件extra表
print()
print('=== 查询所有邮件相关的表 ===')
cursor.execute("SHOW TABLES LIKE '%mail%'")
for row in cursor.fetchall():
    print(row)

# 查询背包装备表，看看正常的装备raw_entry是什么样的
print()
print('=== dnf_inventory_items 表结构 ===')
cursor.execute('DESCRIBE dnf_inventory_items')
for row in cursor.fetchall():
    print(row)

print()
print('=== 查询背包装备（前3条）===')
cursor.execute('SELECT * FROM dnf_inventory_items WHERE collection_name = "inventory" LIMIT 3')
for row in cursor.fetchall():
    print(json.dumps(row, ensure_ascii=False, default=str))
    print()

# 查询背包装备extra表
print()
print('=== 查询所有inventory相关的表 ===')
cursor.execute("SHOW TABLES LIKE '%inventory%'")
for row in cursor.fetchall():
    print(row)

conn.close()
