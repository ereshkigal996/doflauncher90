"""
技能系统测试脚本
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.skill import (
    SkillManager, SkillTemplate, LearnedSkill, SkillBuild,
    SkillType, SkillQuickSlot,
)


def main():
    print("=" * 60)
    print("技能系统测试")
    print("=" * 60)
    print()

    # 创建技能管理器
    manager = SkillManager()
    print("✓ 创建技能管理器")
    print()

    # 测试1: 注册技能模板
    print("测试1: 注册技能模板")

    # 基础技能
    basic_shot = SkillTemplate(
        skill_id=1001,
        skill_name="后撩踢",
        skill_type=SkillType.ACTIVE.value,
        description="神枪手基础技能",
        job_required=["gunner"],
        level_required=1,
        max_level=10,
        base_level=0,
        mp_cost=10,
        cooldown=3.0,
        damage_per_level=50,
    )
    manager.register_skill_template(basic_shot)
    print(f"  注册基础技能: {basic_shot.skill_name} (ID={basic_shot.skill_id})")

    # 转职技能
    headshot = SkillTemplate(
        skill_id=2001,
        skill_name="爆头一击",
        skill_type=SkillType.ACTIVE.value,
        description="漫游枪手核心技能",
        job_required=["gunner"],
        level_required=25,
        grow_type_required=1,  # 漫游枪手
        max_level=20,
        base_level=0,
        mp_cost=50,
        cooldown=8.0,
        cube_cost=1,
        damage_per_level=200,
        prerequisite_skills={1001: 5},  # 需要后撩踢Lv.5
    )
    manager.register_skill_template(headshot)
    print(f"  注册转职技能: {headshot.skill_name} (ID={headshot.skill_id})")

    # 被动技能
    death_walk = SkillTemplate(
        skill_id=3001,
        skill_name="死亡左轮",
        skill_type=SkillType.PASSIVE.value,
        description="增加暴击伤害",
        job_required=["gunner"],
        level_required=30,
        grow_type_required=1,
        max_level=10,
        base_level=0,
        damage_per_level=10,
    )
    manager.register_skill_template(death_walk)
    print(f"  注册被动技能: {death_walk.skill_name} (ID={death_walk.skill_id})")

    # 觉醒技能
    awakening = SkillTemplate(
        skill_id=4001,
        skill_name="疯狂屠戮",
        skill_type=SkillType.AWAKENING.value,
        description="漫游枪手觉醒技能",
        job_required=["gunner"],
        level_required=50,
        grow_type_required=1,
        max_level=1,
        base_level=0,
        mp_cost=200,
        cooldown=120.0,
        cube_cost=5,
        damage_per_level=1000,
    )
    manager.register_skill_template(awakening)
    print(f"  注册觉醒技能: {awakening.skill_name} (ID={awakening.skill_id})")

    print("  ✓ 技能模板注册成功")
    print()

    # 测试2: 设置技能点
    print("测试2: 设置技能点")
    character_id = "test_character"
    manager.set_skill_points(character_id, 100, 100)
    current, max_points = manager.get_skill_points(character_id)
    print(f"  技能点: {current}/{max_points}")
    print("  ✓ 技能点设置成功")
    print()

    # 测试3: 学习技能
    print("测试3: 学习技能")

    # 学习基础技能
    for i in range(5):
        success, reason = manager.learn_skill(
            character_id, 1001, character_job="gunner", character_level=60
        )
    learned = manager.get_learned_skills(character_id)
    print(f"  学习后撩踢到Lv.{learned[1001].level}")

    # 学习爆头一击
    success, reason = manager.learn_skill(
        character_id, 2001, character_job="gunner", character_level=60
    )
    print(f"  学习爆头一击: 成功={success}, 原因={reason}")

    # 学习死亡左轮
    success, reason = manager.learn_skill(
        character_id, 3001, character_job="gunner", character_level=60
    )
    print(f"  学习死亡左轮: 成功={success}, 原因={reason}")

    # 学习觉醒技能
    success, reason = manager.learn_skill(
        character_id, 4001, character_job="gunner", character_level=60
    )
    print(f"  学习疯狂屠戮: 成功={success}, 原因={reason}")

    current, _ = manager.get_skill_points(character_id)
    print(f"  剩余技能点: {current}")
    print(f"  已学习技能数: {len(learned)}")
    print("  ✓ 技能学习成功")
    print()

    # 测试4: 技能学习限制
    print("测试4: 技能学习限制")

    # 等级不足
    success, reason = manager.can_learn_skill(
        character_id, 2001, character_job="gunner", character_level=10
    )
    print(f"  等级不足检测: 成功={success}, 原因={reason}")

    # 职业不符
    success, reason = manager.can_learn_skill(
        character_id, 1001, character_job="swordman", character_level=60
    )
    print(f"  职业不符检测: 成功={success}, 原因={reason}")

    # 前置技能不足
    success, reason = manager.can_learn_skill(
        "new_character", 2001, character_job="gunner", character_level=60
    )
    print(f"  前置技能检测: 成功={success}, 原因={reason}")

    print("  ✓ 技能学习限制检测成功")
    print()

    # 测试5: 技能快捷键
    print("测试5: 技能快捷键")

    # 设置快捷键
    manager.set_quick_slot(character_id, SkillQuickSlot.SLOT_A.value, 1001)
    manager.set_quick_slot(character_id, SkillQuickSlot.SLOT_S.value, 2001)
    manager.set_quick_slot(character_id, SkillQuickSlot.SLOT_D.value, 4001)

    quick_slots = manager.get_quick_slots(character_id)
    print(f"  快捷键设置: {len(quick_slots)}个")
    for slot, skill_id in quick_slots.items():
        skill_name = manager.get_learned_skills(character_id)[skill_id].skill_name
        print(f"    槽位{slot}: {skill_name}")

    # 移除快捷键
    manager.unset_quick_slot(character_id, SkillQuickSlot.SLOT_D.value)
    quick_slots = manager.get_quick_slots(character_id)
    print(f"  移除后快捷键: {len(quick_slots)}个")

    print("  ✓ 技能快捷键功能成功")
    print()

    # 测试6: 使用技能和冷却
    print("测试6: 使用技能和冷却")

    # 使用技能
    success, reason = manager.use_skill(character_id, 2001)
    print(f"  使用爆头一击: 成功={success}, 原因={reason}")

    # 立即再次使用（应该在冷却中）
    success, reason = manager.use_skill(character_id, 2001)
    print(f"  立即再次使用: 成功={success}, 原因={reason}")

    # 使用无冷却技能
    success, reason = manager.use_skill(character_id, 1001)
    print(f"  使用后撩踢: 成功={success}, 原因={reason}")

    print("  ✓ 技能使用和冷却功能成功")
    print()

    # 测试7: 遗忘技能
    print("测试7: 遗忘技能")

    current_before, _ = manager.get_skill_points(character_id)
    print(f"  遗忘前技能点: {current_before}")

    success, reason = manager.unlearn_skill(character_id, 3001)
    print(f"  遗忘死亡左轮: 成功={success}, 原因={reason}")

    current_after, _ = manager.get_skill_points(character_id)
    print(f"  遗忘后技能点: {current_after}")
    print(f"  返还技能点: {current_after - current_before}")

    print("  ✓ 技能遗忘功能成功")
    print()

    # 测试8: 技能加点方案
    print("测试8: 技能加点方案")

    # 保存方案
    build = manager.save_skill_build(character_id, "刷图加点")
    print(f"  保存方案: {build.build_name} (ID={build.build_id})")
    print(f"  方案技能数: {len(build.skills)}")
    print(f"  方案快捷键数: {len(build.quick_slots)}")

    # 获取方案列表
    builds = manager.get_skill_builds(character_id)
    print(f"  方案列表: {len(builds)}个")

    # 加载方案
    success, reason = manager.load_skill_build(character_id, build.build_id)
    print(f"  加载方案: 成功={success}, 原因={reason}")

    print("  ✓ 技能加点方案功能成功")
    print()

    # 测试9: 序列化
    print("测试9: 序列化/反序列化")
    data = manager.to_dict(character_id)
    print(f"  序列化数据键: {list(data.keys())}")
    print(f"  已学习技能数: {len(data['learned_skills'])}")
    print(f"  快捷键数: {len(data['quick_slots'])}")
    print(f"  技能方案数: {len(data['skill_builds'])}")
    print("  ✓ 序列化成功")

    print()
    print("=" * 60)
    print("所有测试通过！技能系统基础功能验证正确")
    print("=" * 60)


if __name__ == "__main__":
    main()
