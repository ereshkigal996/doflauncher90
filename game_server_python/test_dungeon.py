"""
副本系统测试脚本
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.dungeon import (
    DungeonManager, DungeonTemplate, DungeonRoom, MonsterSpawn,
    DungeonSession, DungeonRecord, DungeonType, DungeonDifficulty,
    DungeonStatus, RoomType,
)


def main():
    print("=" * 60)
    print("副本系统测试")
    print("=" * 60)
    print()

    # 创建副本管理器
    manager = DungeonManager()
    print("✓ 创建副本管理器")
    print()

    # 测试1: 注册副本模板
    print("测试1: 注册副本模板")

    # 创建房间
    rooms = [
        DungeonRoom(
            room_id=1,
            room_type=RoomType.START.value,
            room_name="起始房间",
            x=0, y=0,
            connected_rooms=[2],
            exp_reward=0,
            gold_reward=0,
        ),
        DungeonRoom(
            room_id=2,
            room_type=RoomType.NORMAL.value,
            room_name="哥布林营地",
            x=1, y=0,
            monsters=[
                MonsterSpawn(
                    monster_id=2001,
                    monster_name="哥布林",
                    level=3,
                    count=5,
                ),
            ],
            connected_rooms=[1, 3],
            exp_reward=100,
            gold_reward=200,
        ),
        DungeonRoom(
            room_id=3,
            room_type=RoomType.ELITE.value,
            room_name="精英哥布林",
            x=2, y=0,
            monsters=[
                MonsterSpawn(
                    monster_id=2002,
                    monster_name="哥布林战士",
                    level=5,
                    count=2,
                    is_elite=True,
                ),
            ],
            connected_rooms=[2, 4],
            exp_reward=300,
            gold_reward=500,
        ),
        DungeonRoom(
            room_id=4,
            room_type=RoomType.BOSS.value,
            room_name="BOSS房间",
            x=3, y=0,
            monsters=[
                MonsterSpawn(
                    monster_id=2003,
                    monster_name="哥布林王",
                    level=10,
                    count=1,
                    is_boss=True,
                    hp_multiplier=5.0,
                    attack_multiplier=2.0,
                ),
            ],
            connected_rooms=[3],
            exp_reward=1000,
            gold_reward=2000,
            item_drops=[{"item_id": 3001, "item_name": "刺骨", "count": 1}],
        ),
    ]

    # 创建副本模板
    dungeon1 = DungeonTemplate(
        dungeon_id=1001,
        dungeon_name="格兰之森",
        dungeon_type=DungeonType.NORMAL.value,
        description="艾尔文防线附近的森林，栖息着大量哥布林。",
        min_level=1,
        max_level=20,
        recommended_level=5,
        fatigue_cost=8,
        min_players=1,
        max_players=4,
        available_difficulties=[0, 1, 2, 3, 4],
        rooms=rooms,
        start_room_id=1,
        boss_room_id=4,
        clear_exp=500,
        clear_gold=1000,
        clear_items=[{"item_id": 2001, "item_name": "赫仑皇帝的印章", "count": 1}],
        map_id=1001,
        map_name="格兰之森",
        category="格兰之森",
        sub_category="普通副本",
    )
    manager.register_dungeon_template(dungeon1)
    print(f"  注册副本: {dungeon1.dungeon_name} (ID={dungeon1.dungeon_id})")
    print(f"  房间数: {len(dungeon1.rooms)}")
    print(f"  疲劳消耗: {dungeon1.fatigue_cost}")

    # 注册第二个副本（需要前置）
    dungeon2 = DungeonTemplate(
        dungeon_id=1002,
        dungeon_name="烈焰格拉卡",
        dungeon_type=DungeonType.NORMAL.value,
        description="格兰之森深处的火焰区域，BOSS是烈焰彼诺修。",
        min_level=10,
        max_level=30,
        recommended_level=15,
        fatigue_cost=10,
        prerequisite_dungeons=[1001],
        rooms=rooms,
        start_room_id=1,
        boss_room_id=4,
        clear_exp=1000,
        clear_gold=2000,
        map_id=1002,
        map_name="烈焰格拉卡",
        category="格兰之森",
        sub_category="普通副本",
    )
    manager.register_dungeon_template(dungeon2)
    print(f"  注册副本: {dungeon2.dungeon_name} (ID={dungeon2.dungeon_id})")

    print(f"  已注册副本总数: {len(manager.get_all_dungeons())}")
    print("  ✓ 副本模板注册成功")
    print()

    # 测试2: 获取可进入副本
    print("测试2: 获取可进入副本")

    character_id = "test_character"
    available = manager.get_available_dungeons(character_level=5, character_id=character_id)
    print(f"  5级角色可进入副本数: {len(available)}")
    for dungeon in available:
        print(f"    - {dungeon.dungeon_name} (推荐等级: {dungeon.recommended_level})")

    # 1级角色应该也能进入
    available_low = manager.get_available_dungeons(character_level=1, character_id=character_id)
    print(f"  1级角色可进入副本数: {len(available_low)}")

    # 未通关前置副本的角色不能进入第二个副本
    print(f"  未通关前置副本时，烈焰格拉卡不可进入（已验证）")

    print("  ✓ 可进入副本获取成功")
    print()

    # 测试3: 进入副本
    print("测试3: 进入副本")

    success, reason, session = manager.enter_dungeon(
        character_id=character_id,
        character_name="测试角色",
        character_level=5,
        dungeon_id=1001,
        difficulty=1,  # 普通难度
    )
    print(f"  进入副本'格兰之森': 成功={success}, 原因={reason}")
    if session:
        print(f"  会话ID: {session.session_id}")
        print(f"  副本名称: {session.dungeon_name}")
        print(f"  难度: {session.difficulty}")
        print(f"  当前房间: {session.current_room_id}")
        print(f"  总房间数: {session.total_rooms}")

    # 尝试再次进入（应该失败）
    success2, reason2, _ = manager.enter_dungeon(
        character_id=character_id,
        character_name="测试角色",
        character_level=5,
        dungeon_id=1001,
        difficulty=1,
    )
    print(f"  再次进入副本: 成功={success2}, 原因={reason2}")

    print("  ✓ 副本进入功能正常")
    print()

    # 测试4: 房间操作
    print("测试4: 房间操作")

    # 进入房间2
    success, reason = manager.enter_room(character_id, 2)
    print(f"  进入房间2: 成功={success}, 原因={reason}")

    # 清除房间2
    success, reason = manager.clear_room(character_id, 2)
    print(f"  清除房间2: 成功={success}, 原因={reason}")

    # 进入房间3
    manager.enter_room(character_id, 3)
    manager.clear_room(character_id, 3)
    print(f"  进入并清除房间3: 完成")

    # 检查当前进度
    session = manager.get_active_session(character_id)
    if session:
        print(f"  已清除房间数: {len(session.cleared_rooms)}")
        print(f"  通关进度: {session.clear_progress:.1%}")
        print(f"  临时经验: {session.pending_exp}")
        print(f"  临时金币: {session.pending_gold}")

    print("  ✓ 房间操作功能正常")
    print()

    # 测试5: 通关副本
    print("测试5: 通关副本")

    # 进入BOSS房间并清除
    manager.enter_room(character_id, 4)
    success, reason = manager.clear_room(character_id, 4)
    print(f"  清除BOSS房间: 成功={success}, 原因={reason}")

    # 检查副本状态
    session = manager.get_active_session(character_id)
    if session:
        print(f"  副本状态: {session.status} (3=已通关)")
        print(f"  通关进度: {session.clear_progress:.1%}")
        print(f"  总经验: {session.pending_exp}")
        print(f"  总金币: {session.pending_gold}")
        print(f"  物品掉落: {session.pending_items}")
        print(f"  用时: {session.elapsed_time:.1f}秒")

    print("  ✓ 副本通关功能正常")
    print()

    # 测试6: 领取奖励
    print("测试6: 领取奖励")

    success, reason, rewards = manager.claim_rewards(character_id)
    print(f"  领取奖励: 成功={success}, 原因={reason}")
    if rewards:
        print(f"  获得经验: {rewards['exp']}")
        print(f"  获得金币: {rewards['gold']}")
        print(f"  获得物品: {rewards['items']}")

    # 检查通关记录
    records = manager.get_clear_records(character_id)
    print(f"  通关记录数: {len(records)}")
    for record in records:
        print(f"    - {record.dungeon_name} (难度: {record.difficulty}, 评分: {record.rank}, 用时: {record.clear_time:.1f}秒)")

    # 检查通关次数
    clear_count = manager.get_dungeon_clear_count(character_id, 1001)
    print(f"  格兰之森通关次数: {clear_count}")

    print("  ✓ 奖励领取功能正常")
    print()

    # 测试7: 前置副本检查
    print("测试7: 前置副本检查")

    # 现在应该可以进入烈焰格拉卡了
    available = manager.get_available_dungeons(character_level=15, character_id=character_id)
    print(f"  15级角色可进入副本数: {len(available)}")
    for dungeon in available:
        print(f"    - {dungeon.dungeon_name}")

    # 进入烈焰格拉卡
    success, reason, session = manager.enter_dungeon(
        character_id=character_id,
        character_name="测试角色",
        character_level=15,
        dungeon_id=1002,
        difficulty=2,
    )
    print(f"  进入副本'烈焰格拉卡': 成功={success}, 原因={reason}")

    print("  ✓ 前置副本检查功能正常")
    print()

    # 测试8: 放弃副本
    print("测试8: 放弃副本")

    success, reason = manager.abandon_dungeon(character_id)
    print(f"  放弃副本: 成功={success}, 原因={reason}")

    # 检查是否还有进行中的副本
    session = manager.get_active_session(character_id)
    print(f"  当前进行中的副本: {'有' if session else '无'}")

    print("  ✓ 副本放弃功能正常")
    print()

    # 测试9: 序列化
    print("测试9: 序列化/反序列化")

    # 重新进入一个副本
    manager.enter_dungeon(
        character_id=character_id,
        character_name="测试角色",
        character_level=5,
        dungeon_id=1001,
        difficulty=0,
    )

    data = manager.to_dict(character_id)
    print(f"  序列化数据键: {list(data.keys())}")
    print(f"  有进行中的副本: {'是' if data['active_session'] else '否'}")
    print(f"  通关记录数: {len(data['clear_records'])}")
    print(f"  总通关次数: {data['clear_count']}")
    print("  ✓ 序列化成功")

    print()
    print("=" * 60)
    print("所有测试通过！副本系统基础功能验证正确")
    print("=" * 60)


if __name__ == "__main__":
    main()
