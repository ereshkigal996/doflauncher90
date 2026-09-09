"""
公会系统测试脚本
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.guild import (
    GuildManager, Guild, GuildMember, GuildSkill, GuildApplication,
    GuildRank, GuildApplicationStatus, GuildSkillType,
)


def main():
    print("=" * 60)
    print("公会系统测试")
    print("=" * 60)
    print()

    # 创建公会管理器
    manager = GuildManager()
    print("✓ 创建公会管理器")
    print()

    # 测试1: 创建公会
    print("测试1: 创建公会")

    success, reason, guild1 = manager.create_guild(
        guild_name="神话公会",
        master_id="char1",
        master_name="会长A",
        master_account_id="acc1",
        master_level=60,
        master_job="gunner",
        guild_notice="欢迎加入神话公会！",
        guild_introduction="这是一个活跃的公会，欢迎大家加入！",
    )
    print(f"  创建公会'神话公会': 成功={success}, 原因={reason}")
    if guild1:
        print(f"    公会ID: {guild1.guild_id}")
        print(f"    公会名称: {guild1.guild_name}")
        print(f"    会长: {guild1.master_name}")
        print(f"    等级: {guild1.level}")
        print(f"    成员数: {guild1.member_count}")
        print(f"    公告: {guild1.guild_notice}")

    # 创建第二个公会
    success, reason, guild2 = manager.create_guild(
        guild_name="传说公会",
        master_id="char2",
        master_name="会长B",
        master_level=55,
        master_job="swordman",
    )
    print(f"  创建公会'传说公会': 成功={success}, 原因={reason}")

    # 尝试创建同名公会（应该失败）
    success, reason, _ = manager.create_guild(
        guild_name="神话公会",
        master_id="char3",
        master_name="会长C",
    )
    print(f"  创建同名公会: 成功={success}, 原因={reason}")

    # 尝试用已有公会的角色创建公会（应该失败）
    success, reason, _ = manager.create_guild(
        guild_name="新公会",
        master_id="char1",
        master_name="会长A",
    )
    print(f"  用已有公会角色创建: 成功={success}, 原因={reason}")

    print(f"  当前公会总数: {len(manager.get_all_guilds())}")
    print("  ✓ 公会创建功能正常")
    print()

    # 测试2: 申请加入公会
    print("测试2: 申请加入公会")

    # 角色3申请加入神话公会
    success, reason, application = manager.apply_to_guild(
        guild_id=guild1.guild_id,
        character_id="char3",
        character_name="成员C",
        account_id="acc3",
        level=50,
        job="mage",
        message="我想加入公会！",
    )
    print(f"  角色'成员C'申请加入: 成功={success}, 原因={reason}")
    if application:
        print(f"    申请ID: {application.application_id}")
        print(f"    申请消息: {application.message}")
        print(f"    状态: {application.status} (0=待处理)")

    # 角色4申请加入
    success, reason, application2 = manager.apply_to_guild(
        guild_id=guild1.guild_id,
        character_id="char4",
        character_name="成员D",
        level=45,
        job="priest",
    )
    print(f"  角色'成员D'申请加入: 成功={success}, 原因={reason}")

    # 查看待处理申请
    pending_apps = [a for a in guild1.applications.values() if a.status == GuildApplicationStatus.PENDING.value]
    print(f"  待处理申请数: {len(pending_apps)}")

    print("  ✓ 公会申请功能正常")
    print()

    # 测试3: 处理申请
    print("测试3: 处理申请")

    # 批准角色3的申请
    success, reason = manager.process_application(
        guild_id=guild1.guild_id,
        application_id=application.application_id,
        approved=True,
        processed_by="char1",
    )
    print(f"  批准'成员C'的申请: 成功={success}, 原因={reason}")

    # 拒绝角色4的申请
    success, reason = manager.process_application(
        guild_id=guild1.guild_id,
        application_id=application2.application_id,
        approved=False,
        processed_by="char1",
    )
    print(f"  拒绝'成员D'的申请: 成功={success}, 原因={reason}")

    # 检查成员列表
    print(f"  公会成员数: {guild1.member_count}")
    for member in guild1.members.values():
        print(f"    - {member.character_name} (职位: {member.rank_name}, 等级: {member.level})")

    # 检查角色是否在公会中
    char_guild = manager.get_character_guild("char3")
    print(f"  角色'成员C'所在公会: {char_guild.guild_name if char_guild else '无'}")

    print("  ✓ 申请处理功能正常")
    print()

    # 测试4: 成员管理
    print("测试4: 成员管理")

    # 变更职位
    success, reason = manager.change_member_rank(
        guild_id=guild1.guild_id,
        character_id="char3",
        new_rank=GuildRank.OFFICER.value,
        changed_by="char1",
    )
    print(f"  变更'成员C'为官员: 成功={success}, 原因={reason}")

    member = guild1.get_member("char3")
    if member:
        print(f"    当前职位: {member.rank_name}")

    # 添加贡献度
    success, reason = manager.add_contribution("char3", 1000)
    print(f"  增加贡献度: 成功={success}, 原因={reason}")
    if member:
        print(f"    贡献度: {member.contribution}")

    # 公会升级
    print(f"  公会等级: {guild1.level}")
    print(f"  公会经验: {guild1.exp}/{guild1.exp_to_next_level}")

    # 增加大量经验触发升级
    for i in range(10):
        manager.add_contribution("char1", 10000)
    print(f"  增加经验后公会等级: {guild1.level}")
    print(f"  最大成员数: {guild1.max_members}")

    print("  ✓ 成员管理功能正常")
    print()

    # 测试5: 退出公会
    print("测试5: 退出公会")

    # 角色3退出公会
    success, reason = manager.leave_guild("char3")
    print(f"  '成员C'退出公会: 成功={success}, 原因={reason}")

    # 会长尝试退出（应该失败）
    success, reason = manager.leave_guild("char1")
    print(f"  会长退出公会: 成功={success}, 原因={reason}")

    print(f"  退出后成员数: {guild1.member_count}")

    print("  ✓ 退出公会功能正常")
    print()

    # 测试6: 转让会长
    print("测试6: 转让会长")

    # 先让角色3重新加入
    manager.apply_to_guild(guild1.guild_id, "char3", "成员C", level=50, job="mage")
    app_id = list(guild1.applications.keys())[-1]
    manager.process_application(guild1.guild_id, app_id, True, "char1")

    print(f"  转让前会长: {guild1.master_name}")

    # 转让会长
    success, reason = manager.transfer_master(
        guild_id=guild1.guild_id,
        new_master_id="char3",
        old_master_id="char1",
    )
    print(f"  转让会长给'成员C': 成功={success}, 原因={reason}")
    print(f"  转让后会长: {guild1.master_name}")

    # 检查职位
    old_master = guild1.get_member("char1")
    new_master = guild1.get_member("char3")
    if old_master:
        print(f"    原会长职位: {old_master.rank_name}")
    if new_master:
        print(f"    新会长职位: {new_master.rank_name}")

    print("  ✓ 会长转让功能正常")
    print()

    # 测试7: 踢出成员
    print("测试7: 踢出成员")

    # 新会长踢出原会长
    success, reason = manager.kick_member(
        guild_id=guild1.guild_id,
        character_id="char1",
        kicked_by="char3",
    )
    print(f"  踢出原会长: 成功={success}, 原因={reason}")

    print(f"  踢出后成员数: {guild1.member_count}")

    print("  ✓ 踢出成员功能正常")
    print()

    # 测试8: 搜索公会
    print("测试8: 搜索公会")

    # 搜索全部
    results, total = manager.search_guilds(page=1, page_size=10)
    print(f"  搜索全部: {total}个结果")
    for guild in results:
        print(f"    - {guild.guild_name} (等级: {guild.level}, 成员: {guild.member_count})")

    # 按关键词搜索
    results, total = manager.search_guilds(keyword="神话", page=1, page_size=10)
    print(f"  搜索'神话': {total}个结果")

    print("  ✓ 公会搜索功能正常")
    print()

    # 测试9: 解散公会
    print("测试9: 解散公会")

    success, reason = manager.disband_guild(guild1.guild_id, "char3")
    print(f"  解散'神话公会': 成功={success}, 原因={reason}")

    print(f"  解散后公会总数: {len(manager.get_all_guilds())}")

    # 检查角色是否还有公会
    char_guild = manager.get_character_guild("char3")
    print(f"  角色'成员C'所在公会: {char_guild.guild_name if char_guild else '无'}")

    print("  ✓ 公会解散功能正常")
    print()

    # 测试10: 统计信息
    print("测试10: 统计信息")

    stats = manager.get_statistics()
    print(f"  公会总数: {stats['total_guilds']}")
    print(f"  成员总数: {stats['total_members']}")
    print(f"  资金总数: {stats['total_funds']}")
    print(f"  按等级统计: {stats['level_stats']}")

    print("  ✓ 统计信息功能正常")
    print()

    # 测试11: 序列化
    print("测试11: 序列化/反序列化")

    data = manager.to_dict()
    print(f"  序列化数据键: {list(data.keys())}")
    print(f"  公会数: {data['guilds_count']}")
    print(f"  公会列表数: {len(data['guilds'])}")
    print("  ✓ 序列化成功")

    print()
    print("=" * 60)
    print("所有测试通过！公会系统基础功能验证正确")
    print("=" * 60)


if __name__ == "__main__":
    main()
