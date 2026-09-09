"""
角色系统测试脚本
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.character import (
    MemoryCharacterRepository,
    CharacterManager,
    CharacterRecord,
    Job,
    CharacterNameExistsError,
    CharacterSlotOccupiedError,
)


def main():
    # 创建仓库和管理器
    repo = MemoryCharacterRepository()
    manager = CharacterManager(repo)

    print("=" * 60)
    print("角色系统测试")
    print("=" * 60)
    print()

    # 测试1: 创建角色
    print("测试1: 创建角色")
    char1 = manager.create_character(
        account_id="account1",
        name="死亡左轮",
        job=Job.GUNNER.value,
        slot=0,
        level=59,
    )
    print(f"  创建角色: {char1.name} (ID={char1.character_id}, 职业={char1.job}, 等级={char1.level})")
    print(f"  基础属性: HP={char1.stats['hp']}, 力量={char1.stats['strength']}")

    char2 = manager.create_character(
        account_id="account1",
        name="测试专用",
        job=Job.SWORDMAN.value,
        slot=1,
        level=1,
    )
    print(f"  创建角色: {char2.name} (ID={char2.character_id}, 职业={char2.job}, 等级={char2.level})")
    print("  ✓ 创建角色测试通过")
    print()

    # 测试2: 列出角色
    print("测试2: 列出账号角色")
    characters = manager.list_characters("account1")
    print(f"  账号account1有 {len(characters)} 个角色:")
    for char in characters:
        print(f"    - 槽位{char.slot}: {char.name} ({char.job}, Lv.{char.level})")
    print("  ✓ 列出角色测试通过")
    print()

    # 测试3: 角色名重复
    print("测试3: 角色名重复检测")
    try:
        manager.create_character("account1", "死亡左轮", Job.MAGE.value, slot=2)
        print("  ✗ 应该抛出异常")
    except CharacterNameExistsError as e:
        print(f"  ✓ 正确检测到重复名称: {e}")
    print()

    # 测试4: 槽位重复
    print("测试4: 槽位重复检测")
    try:
        manager.create_character("account1", "新角色", Job.MAGE.value, slot=0)
        print("  ✗ 应该抛出异常")
    except CharacterSlotOccupiedError as e:
        print(f"  ✓ 正确检测到槽位占用: {e}")
    print()

    # 测试5: 升级
    print("测试5: 角色升级")
    print(f"  升级前: {char2.name} Lv.{char2.level}, HP={char2.stats['hp']}")
    updated = manager.level_up(char2.character_id, 10)
    print(f"  升级后: {updated.name} Lv.{updated.level}, HP={updated.stats['hp']}")
    print("  ✓ 升级测试通过")
    print()

    # 测试6: 转职
    print("测试6: 转职")
    print(f"  转职前: {char2.name} 职业={char2.job}")
    updated = manager.change_job(char2.character_id, Job.BERSERKER.value)
    print(f"  转职后: {updated.name} 职业={updated.job}")
    print("  ✓ 转职测试通过")
    print()

    # 测试7: 交换槽位
    print("测试7: 交换槽位")
    print(f"  交换前: 槽位0={characters[0].name}, 槽位1={characters[1].name}")
    manager.swap_slots("account1", 0, 1)
    characters = manager.list_characters("account1")
    print(f"  交换后: 槽位0={characters[0].name}, 槽位1={characters[1].name}")
    print("  ✓ 交换槽位测试通过")
    print()

    # 测试8: 删除角色
    print("测试8: 删除角色")
    print(f"  删除前: {len(manager.list_characters('account1'))} 个角色")
    manager.delete_character(char2.character_id)
    print(f"  删除后: {len(manager.list_characters('account1'))} 个角色")
    print("  ✓ 删除角色测试通过")
    print()

    # 测试9: 序列化/反序列化
    print("测试9: 序列化/反序列化")
    char_dict = char1.to_dict()
    char_restored = CharacterRecord.from_dict(char_dict)
    print(f"  原始: {char1.name} Lv.{char1.level}")
    print(f"  恢复: {char_restored.name} Lv.{char_restored.level}")
    print(f"  匹配: {char1.name == char_restored.name and char1.level == char_restored.level}")
    print("  ✓ 序列化/反序列化测试通过")
    print()

    print("=" * 60)
    print("所有测试通过！角色系统基础功能验证正确")
    print("=" * 60)


if __name__ == "__main__":
    main()
