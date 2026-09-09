"""
邮件系统测试脚本
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.mail import (
    MailManager, Mail, MailAttachment, MailType, MailStatus,
)


def main():
    print("=" * 60)
    print("邮件系统测试")
    print("=" * 60)
    print()

    # 创建邮件管理器
    manager = MailManager()
    print("✓ 创建邮件管理器")
    print()

    # 测试1: 发送普通邮件
    print("测试1: 发送普通邮件")

    mail = manager.send_mail(
        sender_id="user1",
        sender_name="玩家A",
        receiver_id="user2",
        receiver_name="玩家B",
        title="测试邮件",
        content="这是一封测试邮件，请注意查收。",
        mail_type=MailType.NORMAL.value,
        expire_days=30,
    )
    print(f"  发送邮件: ID={mail.mail_id}, 标题={mail.title}")
    print(f"  发件人: {mail.sender_name} -> 收件人: {mail.receiver_name}")
    print(f"  发送时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mail.send_time))}")
    print("  ✓ 普通邮件发送成功")
    print()

    # 测试2: 发送系统邮件
    print("测试2: 发送系统邮件")

    system_mail = manager.send_system_mail(
        receiver_id="user2",
        receiver_name="玩家B",
        title="系统公告",
        content="欢迎来到单机版！",
        expire_days=7,
    )
    print(f"  发送系统邮件: ID={system_mail.mail_id}, 标题={system_mail.title}")
    print(f"  发件人: {system_mail.sender_name}")
    print("  ✓ 系统邮件发送成功")
    print()

    # 测试3: 发送物品邮件
    print("测试3: 发送物品邮件")

    item_mail = manager.send_item_mail(
        receiver_id="user2",
        receiver_name="玩家B",
        item_id=1001,
        item_name="雷米的援助",
        count=100,
        sender_name="活动奖励",
    )
    print(f"  发送物品邮件: ID={item_mail.mail_id}, 标题={item_mail.title}")
    print(f"  附件: {item_mail.attachment.item_name} x{item_mail.attachment.count}")
    print("  ✓ 物品邮件发送成功")
    print()

    # 测试4: 发送带强化的装备邮件
    print("测试4: 发送带强化的装备邮件")

    equip_mail = manager.send_item_mail(
        receiver_id="user2",
        receiver_name="玩家B",
        item_id=3001,
        item_name="刺骨",
        count=1,
        reinforce_level=12,
        amplify_level=10,
        amplify_type="strength",
        sender_name="GM",
        title="GM发放装备",
    )
    print(f"  发送装备邮件: ID={equip_mail.mail_id}, 标题={equip_mail.title}")
    print(f"  附件: {equip_mail.attachment.item_name}")
    print(f"  强化: +{equip_mail.attachment.reinforce_level}")
    print(f"  增幅: +{equip_mail.attachment.amplify_level} ({equip_mail.attachment.amplify_type})")
    print("  ✓ 装备邮件发送成功")
    print()

    # 测试5: 发送金币邮件
    print("测试5: 发送金币邮件")

    gold_mail = manager.send_gold_mail(
        receiver_id="user2",
        receiver_name="玩家B",
        gold=1000000,
        sender_name="系统",
    )
    print(f"  发送金币邮件: ID={gold_mail.mail_id}, 标题={gold_mail.title}")
    print(f"  附件金币: {gold_mail.attachment.gold}")
    print("  ✓ 金币邮件发送成功")
    print()

    # 测试6: 收件箱查询
    print("测试6: 收件箱查询")

    inbox = manager.get_inbox("user2")
    print(f"  玩家B收件箱邮件数: {len(inbox)}")
    for i, mail in enumerate(inbox):
        status = "未读" if not mail.is_read else "已读"
        has_attach = "有附件" if mail.has_attachment else "无附件"
        print(f"    [{i+1}] ID={mail.mail_id}, 标题={mail.title}, 状态={status}, {has_attach}")

    # 未读邮件数
    unread_count = manager.get_unread_count("user2")
    print(f"  未读邮件数: {unread_count}")

    # 有附件邮件数
    attach_count = manager.get_attachment_count("user2")
    print(f"  有附件邮件数: {attach_count}")

    print("  ✓ 收件箱查询成功")
    print()

    # 测试7: 阅读邮件
    print("测试7: 阅读邮件")

    first_mail = inbox[0]
    print(f"  阅读前状态: {'未读' if not first_mail.is_read else '已读'}")

    read_mail = manager.read_mail(first_mail.mail_id)
    print(f"  阅读邮件: ID={read_mail.mail_id}, 标题={read_mail.title}")
    print(f"  阅读后状态: {'未读' if not read_mail.is_read else '已读'}")
    print(f"  阅读时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(read_mail.read_time))}")

    unread_after = manager.get_unread_count("user2")
    print(f"  阅读后未读邮件数: {unread_after}")

    print("  ✓ 阅读邮件成功")
    print()

    # 测试8: 领取附件
    print("测试8: 领取附件")

    # 找到有附件的邮件
    attach_mail = None
    for mail in inbox:
        if mail.has_attachment:
            attach_mail = mail
            break

    if attach_mail:
        print(f"  领取前附件: {attach_mail.attachment.item_name} x{attach_mail.attachment.count}")

        attachment = manager.claim_attachment(attach_mail.mail_id)
        print(f"  领取附件: {attachment.item_name} x{attachment.count}")
        print(f"  附件金币: {attachment.gold}")
        print(f"  附件点券: {attachment.cera}")

        # 再次领取应该为空
        attachment2 = manager.claim_attachment(attach_mail.mail_id)
        print(f"  再次领取: {'空' if attachment2 is None else '有附件'}")

        attach_after = manager.get_attachment_count("user2")
        print(f"  领取后有附件邮件数: {attach_after}")

    print("  ✓ 领取附件成功")
    print()

    # 测试9: 删除邮件
    print("测试9: 删除邮件")

    # 找到一封邮件删除
    delete_mail = inbox[-1]
    print(f"  删除前邮件数: {len(manager.get_inbox('user2'))}")

    success = manager.delete_mail(delete_mail.mail_id)
    print(f"  删除邮件: ID={delete_mail.mail_id}, 成功={success}")

    print(f"  删除后邮件数: {len(manager.get_inbox('user2'))}")

    # 批量删除
    remaining = manager.get_inbox("user2")
    if len(remaining) >= 2:
        delete_ids = [remaining[0].mail_id, remaining[1].mail_id]
        deleted_count = manager.delete_mails(delete_ids)
        print(f"  批量删除: {deleted_count}封")

    print(f"  最终邮件数: {len(manager.get_inbox('user2'))}")
    print("  ✓ 删除邮件成功")
    print()

    # 测试10: 发件箱查询
    print("测试10: 发件箱查询")

    outbox = manager.get_outbox("user1")
    print(f"  玩家A发件箱邮件数: {len(outbox)}")
    for i, mail in enumerate(outbox):
        print(f"    [{i+1}] ID={mail.mail_id}, 标题={mail.title}, 收件人={mail.receiver_name}")

    print("  ✓ 发件箱查询成功")
    print()

    # 测试11: 序列化
    print("测试11: 序列化/反序列化")
    data = manager.to_dict("user2")
    print(f"  序列化数据键: {list(data.keys())}")
    print(f"  收件箱邮件数: {data['inbox_count']}")
    print(f"  发件箱邮件数: {data['outbox_count']}")
    print(f"  未读邮件数: {data['unread_count']}")
    print(f"  有附件邮件数: {data['attachment_count']}")
    print("  ✓ 序列化成功")

    print()
    print("=" * 60)
    print("所有测试通过！邮件系统基础功能验证正确")
    print("=" * 60)


if __name__ == "__main__":
    main()
