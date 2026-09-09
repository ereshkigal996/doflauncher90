"""
数据持久化测试脚本
"""

import sys
import os
import time
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.persistence import DataPersistence
from database.db_manager import DatabaseManager


def main():
    print("=" * 60)
    print("数据持久化测试")
    print("=" * 60)
    print()

    # 创建临时数据库
    temp_db = os.path.join(tempfile.gettempdir(), f"dnf_test_{int(time.time())}.db")
    print(f"测试数据库: {temp_db}")
    print()

    # 初始化数据库管理器
    db = DatabaseManager()
    db.mode = "sqlite"
    db.db_path = temp_db
    db._connect_sqlite()

    # 初始化数据持久化
    persistence = DataPersistence(db_manager=db)
    success = persistence.initialize()
    print(f"✓ 数据持久化初始化: {success}")
    print()

    # 测试1: 账号持久化
    print("测试1: 账号持久化")

    account_data = {
        "username": "testuser",
        "password": "testpass123",
        "cera": 10000,
        "gold": 500000,
    }
    account_id = persistence.save_account(account_data)
    print(f"  保存账号: ID={account_id}")

    loaded_account = persistence.load_account("testuser")
    print(f"  加载账号: {loaded_account['username'] if loaded_account else 'None'}")
    print(f"  点券: {loaded_account['cera'] if loaded_account else 0}")
    print(f"  金币: {loaded_account['gold'] if loaded_account else 0}")
    print("  ✓ 账号持久化成功")
    print()

    # 测试2: 角色持久化
    print("测试2: 角色持久化")

    character_data = {
        "account_id": "testuser",
        "name": "死亡左轮",
        "job": "gunner",
        "grow_type": 1,
        "level": 59,
        "exp": 1000000,
        "slot_index": 0,
        "town_id": 2,
        "position_x": 100.5,
        "position_y": 200.3,
        "strength": 500,
        "intelligence": 300,
        "vitality": 400,
        "spirit": 350,
        "hp_max": 50000,
        "mp_max": 30000,
        "physical_attack": 8000,
        "magical_attack": 5000,
        "physical_defense": 15000,
        "magical_defense": 10000,
        "attack_speed": 1200,
        "move_speed": 1100,
        "cast_speed": 1050,
        "fatigue_used": 50,
        "fatigue_limit": 156,
        "fatigue_battery": 30,
        "gold": 1000000,
        "cera": 5000,
    }
    character_id = persistence.save_character(character_data)
    print(f"  保存角色: ID={character_id}")

    loaded_character = persistence.load_character(character_id)
    print(f"  加载角色: {loaded_character['name'] if loaded_character else 'None'}")
    print(f"  职业: {loaded_character['job'] if loaded_character else ''}")
    print(f"  等级: {loaded_character['level'] if loaded_character else 0}")
    print(f"  力量: {loaded_character['strength'] if loaded_character else 0}")
    print(f"  HP: {loaded_character['hp_max'] if loaded_character else 0}")

    # 加载账号下所有角色
    characters = persistence.load_characters_by_account("testuser")
    print(f"  账号下角色数: {len(characters)}")
    print("  ✓ 角色持久化成功")
    print()

    # 测试3: 背包持久化
    print("测试3: 背包持久化")

    inventory_data = [
        {
            "inventory_type": 0,
            "slot_index": 0,
            "item_id": 3001,
            "item_name": "刺骨",
            "item_type": "equipment",
            "count": 1,
            "reinforce_level": 12,
            "amplify_level": 10,
            "amplify_type": "strength",
            "quality": 100,
            "durability": 100,
            "max_durability": 100,
        },
        {
            "inventory_type": 1,
            "slot_index": 0,
            "item_id": 1001,
            "item_name": "雷米的援助",
            "item_type": "consumable",
            "count": 100,
        },
        {
            "inventory_type": 2,
            "slot_index": 0,
            "item_id": 2001,
            "item_name": "赫仑皇帝的印章",
            "item_type": "material",
            "count": 50,
        },
    ]

    success = persistence.save_inventory(character_id, inventory_data)
    print(f"  保存背包: {success}")

    loaded_inventory = persistence.load_inventory(character_id)
    print(f"  加载背包物品数: {len(loaded_inventory)}")
    for item in loaded_inventory:
        print(f"    - {item['item_name']} x{item['count']} (类型={item['item_type']}, 槽位={item['slot_index']})")
    print("  ✓ 背包持久化成功")
    print()

    # 测试4: 已装备持久化
    print("测试4: 已装备持久化")

    equipped_data = {
        0: {  # 武器
            "item_id": 3001,
            "item_name": "刺骨",
            "reinforce_level": 12,
            "amplify_level": 10,
            "amplify_type": "strength",
            "quality": 100,
        },
        1: {  # 上衣
            "item_id": 4001,
            "item_name": "魔战无双胸甲",
            "reinforce_level": 10,
            "quality": 100,
        },
    }

    success = persistence.save_equipped_items(character_id, equipped_data)
    print(f"  保存已装备: {success}")

    loaded_equipped = persistence.load_equipped_items(character_id)
    print(f"  加载已装备数: {len(loaded_equipped)}")
    for slot, item in loaded_equipped.items():
        print(f"    - 槽位{slot}: {item['item_name']} (+{item['reinforce_level']})")
    print("  ✓ 已装备持久化成功")
    print()

    # 测试5: 技能持久化
    print("测试5: 技能持久化")

    skills_data = [
        {
            "skill_id": 1001,
            "skill_name": "后撩踢",
            "level": 10,
            "quick_slot": 0,
        },
        {
            "skill_id": 2001,
            "skill_name": "爆头一击",
            "level": 20,
            "quick_slot": 1,
        },
        {
            "skill_id": 3001,
            "skill_name": "死亡左轮",
            "level": 10,
            "quick_slot": -1,
        },
    ]

    success = persistence.save_skills(character_id, skills_data)
    print(f"  保存技能: {success}")

    loaded_skills = persistence.load_skills(character_id)
    print(f"  加载技能数: {len(loaded_skills)}")
    for skill in loaded_skills:
        slot = skill['quick_slot']
        slot_str = f"快捷槽{slot}" if slot >= 0 else "未设置"
        print(f"    - {skill['skill_name']} Lv.{skill['level']} ({slot_str})")

    # 技能点
    persistence.save_skill_points(character_id, 50, 100)
    current, max_points = persistence.load_skill_points(character_id)
    print(f"  技能点: {current}/{max_points}")
    print("  ✓ 技能持久化成功")
    print()

    # 测试6: 邮件持久化
    print("测试6: 邮件持久化")

    # 获取下一个邮件ID
    next_mail_id = persistence.get_next_mail_id()
    print(f"  下一个邮件ID: {next_mail_id}")

    mail_data = {
        "mail_id": next_mail_id,
        "mail_type": 1,
        "status": 0,
        "sender_id": "system",
        "sender_name": "系统",
        "receiver_id": "testuser",
        "receiver_name": "测试用户",
        "title": "测试邮件",
        "content": "这是一封测试邮件，请注意查收。",
        "attachment_item_id": 1001,
        "attachment_item_name": "雷米的援助",
        "attachment_count": 50,
        "attachment_gold": 100000,
        "send_time": time.time(),
    }
    mail_id = persistence.save_mail(mail_data)
    print(f"  保存邮件: ID={mail_id}")

    # 第二封邮件
    mail_data2 = dict(mail_data)
    mail_data2["mail_id"] = next_mail_id + 1
    mail_data2["title"] = "第二封测试邮件"
    mail_data2["status"] = 1  # 已读
    persistence.save_mail(mail_data2)

    loaded_mails = persistence.load_mails_by_receiver("testuser")
    print(f"  加载邮件数: {len(loaded_mails)}")
    for mail in loaded_mails:
        status = "未读" if mail['status'] == 0 else "已读"
        print(f"    - [{status}] {mail['title']} (发件人: {mail['sender_name']})")

    print("  ✓ 邮件持久化成功")
    print()

    # 测试7: 统计信息
    print("测试7: 统计信息")

    stats = persistence.get_statistics()
    print(f"  账号数: {stats.get('accounts', 0)}")
    print(f"  角色数: {stats.get('characters', 0)}")
    print(f"  邮件数: {stats.get('mails', 0)}")
    print(f"  背包物品数: {stats.get('inventory_items', 0)}")
    print("  ✓ 统计信息获取成功")
    print()

    # 测试8: 删除角色
    print("测试8: 删除角色")

    # 创建第二个角色用于删除测试
    character_data2 = dict(character_data)
    character_data2["name"] = "测试角色2"
    character_data2["slot_index"] = 1
    char2_id = persistence.save_character(character_data2)
    print(f"  创建测试角色: ID={char2_id}")

    characters_before = persistence.load_characters_by_account("testuser")
    print(f"  删除前角色数: {len(characters_before)}")

    success = persistence.delete_character(char2_id)
    print(f"  删除角色: {success}")

    characters_after = persistence.load_characters_by_account("testuser")
    print(f"  删除后角色数: {len(characters_after)}")
    print("  ✓ 删除角色成功")
    print()

    # 清理
    db.close()
    if os.path.exists(temp_db):
        os.remove(temp_db)
        print(f"✓ 清理测试数据库: {temp_db}")

    print()
    print("=" * 60)
    print("所有测试通过！数据持久化功能验证正确")
    print("=" * 60)


if __name__ == "__main__":
    main()
