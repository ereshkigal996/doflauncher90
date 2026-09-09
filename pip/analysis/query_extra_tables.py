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

# 查询邮件附件extra表结构
print('=== dnf_mail_attachment_extra 表结构 ===')
cursor.execute('DESCRIBE dnf_mail_attachment_extra')
for row in cursor.fetchall():
    print(row)

print()
print('=== 查询邮件附件extra数据（前10条）===')
cursor.execute('SELECT * FROM dnf_mail_attachment_extra LIMIT 10')
for row in cursor.fetchall():
    print(json.dumps(row, ensure_ascii=False, default=str))

# 查询背包装备extra表结构
print()
print('=== dnf_inventory_item_extra 表结构 ===')
cursor.execute('DESCRIBE dnf_inventory_item_extra')
for row in cursor.fetchall():
    print(row)

print()
print('=== 查询背包装备extra数据（前10条）===')
cursor.execute('SELECT * FROM dnf_inventory_item_extra LIMIT 10')
for row in cursor.fetchall():
    print(json.dumps(row, ensure_ascii=False, default=str))

# 查询一个有强化增幅的装备，看看它的extra数据
print()
print('=== 查询有强化的装备extra数据 ===')
cursor.execute("SELECT * FROM dnf_inventory_item_extra WHERE extra_key IN ('reinforce', 'upgrade_level', 'amplify_type', 'amplify_value') LIMIT 20")
for row in cursor.fetchall():
    print(json.dumps(row, ensure_ascii=False, default=str))

conn.close()
