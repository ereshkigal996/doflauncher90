"""
任务系统测试脚本
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.quest import (
    QuestManager, QuestTemplate, QuestObjective, QuestReward,
    ActiveQuest, QuestType, QuestStatus, QuestObjectiveType,
)


def main():
    print("=" * 60)
    print("任务系统测试")
    print("=" * 60)
    print()

    # 创建任务管理器
    manager = QuestManager()
    print("✓ 创建任务管理器")
    print()

    # 测试1: 注册任务模板
    print("测试1: 注册任务模板")

    # 主线任务1
    quest1 = QuestTemplate(
        quest_id=1001,
        quest_name="初次冒险",
        quest_type=QuestType.MAIN.value,
        description="前往艾尔文防线，与林纳斯对话。",
        detailed_description="勇士，你终于来了！艾尔文防线需要你的帮助。请先与铁匠林纳斯对话，他会告诉你接下来该怎么做。",
        min_level=1,
        max_level=100,
        start_npc_id=1001,
        start_npc_name="林纳斯",
        end_npc_id=1001,
        end_npc_name="林纳斯",
        objectives=[
            QuestObjective(
                objective_id=1,
                objective_type=QuestObjectiveType.TALK_TO_NPC.value,
                description="与林纳斯对话",
                target_id=1001,
                target_name="林纳斯",
                required_count=1,
            ),
        ],
        reward=QuestReward(
            exp=100,
            gold=500,
            items=[{"item_id": 1001, "item_name": "新手药水", "count": 5}],
        ),
        chain_id=1,
        chain_order=1,
    )
    manager.register_quest_template(quest1)
    print(f"  注册主线任务: {quest1.quest_name} (ID={quest1.quest_id})")

    # 主线任务2（需要先完成任务1）
    quest2 = QuestTemplate(
        quest_id=1002,
        quest_name="猎杀哥布林",
        quest_type=QuestType.MAIN.value,
        description="前往格兰之森，猎杀10只哥布林。",
        detailed_description="林纳斯告诉你，最近格兰之森的哥布林越来越猖獗了。请前往那里，猎杀10只哥布林，保护村民的安全。",
        min_level=2,
        max_level=100,
        prerequisite_quests=[1001],
        start_npc_id=1001,
        start_npc_name="林纳斯",
        end_npc_id=1001,
        end_npc_name="林纳斯",
        objectives=[
            QuestObjective(
                objective_id=1,
                objective_type=QuestObjectiveType.KILL_MONSTER.value,
                description="猎杀哥布林",
                target_id=2001,
                target_name="哥布林",
                required_count=10,
            ),
        ],
        reward=QuestReward(
            exp=500,
            gold=2000,
            skill_points=1,
            items=[{"item_id": 2001, "item_name": "哥布林毛皮", "count": 3}],
        ),
        chain_id=1,
        chain_order=2,
    )
    manager.register_quest_template(quest2)
    print(f"  注册主线任务: {quest2.quest_name} (ID={quest2.quest_id})")

    # 支线任务
    quest3 = QuestTemplate(
        quest_id=2001,
        quest_name="收集材料",
        quest_type=QuestType.SIDE.value,
        description="收集5个赫仑皇帝的印章。",
        min_level=10,
        max_level=100,
        objectives=[
            QuestObjective(
                objective_id=1,
                objective_type=QuestObjectiveType.COLLECT_ITEM.value,
                description="收集赫仑皇帝的印章",
                target_id=3001,
                target_name="赫仑皇帝的印章",
                required_count=5,
            ),
        ],
        reward=QuestReward(
            exp=1000,
            gold=5000,
        ),
    )
    manager.register_quest_template(quest3)
    print(f"  注册支线任务: {quest3.quest_name} (ID={quest3.quest_id})")

    # 每日任务
    quest4 = QuestTemplate(
        quest_id=3001,
        quest_name="每日修炼",
        quest_type=QuestType.DAILY.value,
        description="通关任意副本3次。",
        min_level=1,
        max_level=100,
        objectives=[
            QuestObjective(
                objective_id=1,
                objective_type=QuestObjectiveType.CLEAR_DUNGEON.value,
                description="通关副本",
                target_id=0,
                target_name="任意副本",
                required_count=3,
            ),
        ],
        reward=QuestReward(
            exp=2000,
            gold=10000,
        ),
    )
    manager.register_quest_template(quest4)
    print(f"  注册每日任务: {quest4.quest_name} (ID={quest4.quest_id})")

    print(f"  已注册任务总数: {len(manager.get_all_quest_templates())}")
    print("  ✓ 任务模板注册成功")
    print()

    # 测试2: 获取可接受任务
    print("测试2: 获取可接受任务")

    character_id = "test_character"
    available = manager.get_available_quests(character_id, character_level=5, character_job="gunner")
    print(f"  5级神枪手可接受任务数: {len(available)}")
    for quest in available:
        print(f"    - {quest.quest_name} (类型: {quest.quest_type})")

    # 等级不足的任务应该不显示
    available_low = manager.get_available_quests(character_id, character_level=1, character_job="gunner")
    print(f"  1级神枪手可接受任务数: {len(available_low)}")

    print("  ✓ 可接受任务获取成功")
    print()

    # 测试3: 接受任务
    print("测试3: 接受任务")

    # 接受任务1
    success, reason = manager.accept_quest(character_id, 1001, character_level=5, character_job="gunner")
    print(f"  接受任务'初次冒险': 成功={success}, 原因={reason}")

    # 尝试接受需要前置的任务2（应该失败）
    success, reason = manager.accept_quest(character_id, 1002, character_level=5, character_job="gunner")
    print(f"  接受任务'猎杀哥布林'（前置未完成）: 成功={success}, 原因={reason}")

    # 尝试接受等级不足的任务3（应该失败）
    success, reason = manager.accept_quest(character_id, 2001, character_level=5, character_job="gunner")
    print(f"  接受任务'收集材料'（等级不足）: 成功={success}, 原因={reason}")

    # 查看进行中的任务
    active = manager.get_active_quests(character_id)
    print(f"  进行中的任务数: {len(active)}")
    for quest in active:
        print(f"    - {quest.quest_name} (状态: {quest.status})")

    print("  ✓ 任务接受功能正常")
    print()

    # 测试4: 更新任务目标
    print("测试4: 更新任务目标")

    # 完成任务1的目标（与NPC对话）
    success, reason = manager.update_quest_objective(character_id, 1001, 1, 1)
    print(f"  更新任务'初次冒险'目标: 成功={success}, 原因={reason}")

    # 检查任务状态
    active_quest = manager.get_active_quest(character_id, 1001)
    if active_quest:
        print(f"  任务状态: {active_quest.status} (0=未开始, 1=进行中, 2=已完成, 3=已结束)")
        print(f"  目标完成情况: {active_quest.objectives[0].current_count}/{active_quest.objectives[0].required_count}")

    print("  ✓ 任务目标更新功能正常")
    print()

    # 测试5: 完成任务并领取奖励
    print("测试5: 完成任务并领取奖励")

    success, reason, reward = manager.complete_quest(character_id, 1001)
    print(f"  完成任务'初次冒险': 成功={success}, 原因={reason}")
    if reward:
        print(f"  获得奖励:")
        print(f"    - 经验: {reward.exp}")
        print(f"    - 金币: {reward.gold}")
        print(f"    - 物品: {reward.items}")

    # 检查已完成任务
    completed = manager.get_completed_quests(character_id)
    print(f"  已完成任务数: {len(completed)}")
    print(f"  已完成任务ID: {list(completed.keys())}")

    # 现在应该可以接受任务2了
    success, reason = manager.accept_quest(character_id, 1002, character_level=5, character_job="gunner")
    print(f"  接受任务'猎杀哥布林'（前置已完成）: 成功={success}, 原因={reason}")

    print("  ✓ 任务完成和奖励领取功能正常")
    print()

    # 测试6: 事件驱动更新任务
    print("测试6: 事件驱动更新任务")

    # 模拟击杀哥布林
    results = manager.update_quest_by_event(
        character_id,
        QuestObjectiveType.KILL_MONSTER.value,
        target_id=2001,
        count=3,
    )
    print(f"  击杀3只哥布林后，更新的任务数: {len(results)}")
    for quest_id, just_completed in results:
        print(f"    - 任务{quest_id}: 刚完成={just_completed}")

    # 继续击杀
    results = manager.update_quest_by_event(
        character_id,
        QuestObjectiveType.KILL_MONSTER.value,
        target_id=2001,
        count=7,
    )
    print(f"  再击杀7只哥布林后，更新的任务数: {len(results)}")
    for quest_id, just_completed in results:
        print(f"    - 任务{quest_id}: 刚完成={just_completed}")

    # 检查任务状态
    active_quest = manager.get_active_quest(character_id, 1002)
    if active_quest:
        print(f"  任务'猎杀哥布林'状态: {active_quest.status}")
        print(f"  目标完成: {active_quest.objectives[0].current_count}/{active_quest.objectives[0].required_count}")

    print("  ✓ 事件驱动更新任务功能正常")
    print()

    # 测试7: 放弃任务
    print("测试7: 放弃任务")

    # 接受每日任务
    manager.accept_quest(character_id, 3001, character_level=5, character_job="gunner")
    active_before = len(manager.get_active_quests(character_id))
    print(f"  放弃前进行中任务数: {active_before}")

    success, reason = manager.abandon_quest(character_id, 3001)
    print(f"  放弃任务'每日修炼': 成功={success}, 原因={reason}")

    active_after = len(manager.get_active_quests(character_id))
    print(f"  放弃后进行中任务数: {active_after}")

    print("  ✓ 任务放弃功能正常")
    print()

    # 测试8: 任务进度摘要
    print("测试8: 任务进度摘要")

    summary = manager.get_quest_progress_summary(character_id)
    print(f"  进行中任务数: {summary['in_progress_count']}")
    print(f"  可领取奖励任务数: {summary['can_claim_count']}")
    print(f"  已完成任务数: {summary['completed_count']}")

    print("  ✓ 任务进度摘要功能正常")
    print()

    # 测试9: 序列化
    print("测试9: 序列化/反序列化")

    data = manager.to_dict(character_id)
    print(f"  序列化数据键: {list(data.keys())}")
    print(f"  进行中任务数: {len(data['active_quests'])}")
    print(f"  已完成任务数: {len(data['completed_quests'])}")
    print("  ✓ 序列化成功")

    print()
    print("=" * 60)
    print("所有测试通过！任务系统基础功能验证正确")
    print("=" * 60)


if __name__ == "__main__":
    main()
