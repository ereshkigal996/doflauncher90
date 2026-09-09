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

# 查询邮件主表结构
print('=== dnf_mails 表结构 ===')
cursor.execute('DESCRIBE dnf_mails')
for row in cursor.fetchall():
    print(row)

print()
print('=== 查询最近的邮件（前3条）===')
cursor.execute('SELECT * FROM dnf_mails ORDER BY created_at DESC LIMIT 3')
for row in cursor.fetchall():
    print(json.dumps(row, ensure_ascii=False, default=str))
    print()

# 查询邮件附件表结构
print('=== dnf_mail_attachments 表结构 ===')
cursor.execute('DESCRIBE dnf_mail_attachments')
for row in cursor.fetchall():
    print(row)

print()
print('=== 查询最近的邮件附件（前5条）===')
cursor.execute('SELECT * FROM dnf_mail_attachments ORDER BY character_id DESC, mail_id DESC LIMIT 5')
for row in cursor.fetchall():
    print(json.dumps(row, ensure_ascii=False, default=str))
    print()

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

# 查询我们发放的邮件（GM 物品发放）
print()
print('=== 查询我们发放的邮件（GM 物品发放）===')
cursor.execute("SELECT * FROM dnf_mails WHERE title = 'GM 物品发放' ORDER BY created_at DESC LIMIT 3")
for row in cursor.fetchall():
    print(json.dumps(row, ensure_ascii=False, default=str))
    print()
    # 查询对应的邮件附件
    mail_id = row.get('mail_id')
    char_id = row.get('character_id')
    cursor.execute(f"SELECT * FROM dnf_mail_attachments WHERE character_id = '{char_id}' AND mail_id = '{mail_id}'")
    for att in cursor.fetchall():
        print('  附件:', json.dumps(att, ensure_ascii=False, default=str))
    print()

conn.close()
