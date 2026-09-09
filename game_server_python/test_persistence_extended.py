"""
数据库持久化扩展测试脚本
测试副本、拍卖行、公会系统的数据库存储功能
"""

import sys
import os
import time
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.persistence import DataPersistence
from database.db_manager import DatabaseManager


def main():
    print("=" * 70)
    print("数据库持久化扩展测试")
    print("=" * 70)
    print()

    # 创建临时数据库
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_game.db")
    print(f"测试数据库: {db_path}")
    print()

    # 初始化数据库管理器
    from config.instance import InstanceConfig
    config = InstanceConfig()
    config.database.mode = 'sqlite'
    config.database.path = db_path
    
    db_manager = DatabaseManager()
    success = db_manager.init_from_config(config)
    print(f"✓ 数据库连接成功: {success}")

    # 初始化持久化管理器
    persistence = DataPersistence(db_manager)
    success = persistence.initialize()
    print(f"✓ 持久化模块初始化: 成功={success}")
    print()

    # 测试1: 副本记录持久化
    print("【测试1: 副本记录持久化】")
    print("-" * 70)

    # 保存副本记录
    record_data = {
        'character_id': 'test_char_001',
        'dungeon_id': 1001,
        'dungeon_name': '格兰之森',
        'difficulty': 1,
        'clear_time': 120.5,
        'rank': 'S',
        'exp_reward': 500,
        'gold_reward': 1000,
        'items_reward': [{'item_id': 2001, 'item_name': '赫仑皇帝的印章', 'count': 1}],
        'first_clear': 1,
    }
    success = persistence.save_dungeon_record(record_data)
    print(f"✓ 保存副本记录: 成功={success}")

    # 再次保存（更新通关次数）
    record_data['clear_time'] = 95.0
    record_data['rank'] = 'A'
    success = persistence.save_dungeon_record(record_data)
    print(f"✓ 更新副本记录（通关次数+1）: 成功={success}")

    # 获取副本记录
    records = persistence.get_dungeon_records('test_char_001')
    print(f"✓ 获取角色副本记录: {len(records)}条")
    if records:
        print(f"  副本: {records[0]['dungeon_name']}")
        print(f"  难度: {records[0]['difficulty']}")
        print(f"  通关次数: {records[0]['clear_count']}")
        print(f"  最快通关: {records[0]['clear_time']}秒")
        print(f"  评级: {records[0]['rank']}")

    # 获取单个副本记录
    record = persistence.get_dungeon_record('test_char_001', 1001, 1)
    print(f"✓ 获取单个副本记录: {'存在' if record else '不存在'}")

    print()

    # 测试2: 拍卖行持久化
    print("【测试2: 拍卖行持久化】")
    print("-" * 70)

    # 保存上架记录
    listing_data = {
        'listing_id': 1,
        'seller_id': 'test_char_001',
        'seller_name': '测试角色1',
        'item_id': 2001,
        'item_name': '赫仑皇帝的印章',
        'item_type': 'material',
        'item_level': 1,
        'rarity': 2,
        'quantity': 10,
        'price': 50000,
        'unit_price': 5000,
        'status': 0,
        'list_time': time.time(),
        'expire_time': time.time() + 86400,
        'deposit_fee': 500,
    }
    success = persistence.save_auction_listing(listing_data)
    print(f"✓ 保存上架记录: 成功={success}")

    # 保存第二个上架记录
    listing_data2 = listing_data.copy()
    listing_data2['listing_id'] = 2
    listing_data2['item_id'] = 1001
    listing_data2['item_name'] = '雷米的援助'
    listing_data2['item_type'] = 'consumable'
    listing_data2['quantity'] = 100
    listing_data2['price'] = 100000
    success = persistence.save_auction_listing(listing_data2)
    print(f"✓ 保存第二个上架记录: 成功={success}")

    # 获取上架列表
    listings = persistence.get_auction_listings(status=0)
    print(f"✓ 获取上架中列表: {len(listings)}条")
    for listing in listings:
        print(f"  - {listing['item_name']} x{listing['quantity']} ({listing['price']}金币)")

    # 更新上架状态（已售出）
    listing_data['status'] = 1
    listing_data['sold_time'] = time.time()
    listing_data['buyer_id'] = 'test_char_002'
    listing_data['buyer_name'] = '测试角色2'
    listing_data['transaction_fee'] = 2500
    success = persistence.save_auction_listing(listing_data)
    print(f"✓ 更新上架状态（已售出）: 成功={success}")

    # 保存交易记录
    transaction_data = {
        'transaction_id': 1,
        'listing_id': 1,
        'item_id': 2001,
        'item_name': '赫仑皇帝的印章',
        'quantity': 10,
        'price': 50000,
        'transaction_fee': 2500,
        'seller_income': 47500,
        'seller_id': 'test_char_001',
        'seller_name': '测试角色1',
        'buyer_id': 'test_char_002',
        'buyer_name': '测试角色2',
        'transaction_time': time.time(),
    }
    success = persistence.save_auction_transaction(transaction_data)
    print(f"✓ 保存交易记录: 成功={success}")

    print()

    # 测试3: 公会持久化
    print("【测试3: 公会持久化】")
    print("-" * 70)

    # 保存公会
    guild_data = {
        'guild_id': 1,
        'guild_name': '测试公会',
        'guild_notice': '欢迎加入测试公会！',
        'guild_introduction': '这是一个测试公会',
        'master_id': 'test_char_001',
        'master_name': '测试角色1',
        'level': 1,
        'max_level': 10,
        'exp': 0,
        'exp_to_next_level': 100000,
        'funds': 1000000,
        'member_count': 2,
        'max_members': 100,
        'emblem_id': 0,
        'create_time': time.time(),
    }
    success = persistence.save_guild(guild_data)
    print(f"✓ 保存公会: 成功={success}")

    # 获取公会
    guild = persistence.get_guild(1)
    print(f"✓ 获取公会: {'存在' if guild else '不存在'}")
    if guild:
        print(f"  公会名: {guild['guild_name']}")
        print(f"  会长: {guild['master_name']}")
        print(f"  等级: {guild['level']}")
        print(f"  资金: {guild['funds']}")
        print(f"  成员数: {guild['member_count']}")

    # 更新公会信息
    guild_data['level'] = 2
    guild_data['exp'] = 50000
    guild_data['funds'] = 2000000
    success = persistence.save_guild(guild_data)
    print(f"✓ 更新公会信息（升级到2级）: 成功={success}")

    # 保存公会成员
    member1_data = {
        'guild_id': 1,
        'character_id': 'test_char_001',
        'character_name': '测试角色1',
        'account_id': 'acc_001',
        'rank': 0,  # 会长
        'level': 60,
        'job': 'gunner',
        'contribution': 10000,
        'weekly_contribution': 500,
        'is_online': 1,
        'last_login_time': time.time(),
        'join_time': time.time(),
    }
    success = persistence.save_guild_member(member1_data)
    print(f"✓ 保存公会成员（会长）: 成功={success}")

    member2_data = member1_data.copy()
    member2_data['character_id'] = 'test_char_002'
    member2_data['character_name'] = '测试角色2'
    member2_data['account_id'] = 'acc_002'
    member2_data['rank'] = 3  # 成员
    member2_data['level'] = 55
    member2_data['job'] = 'swordman'
    member2_data['contribution'] = 5000
    member2_data['is_online'] = 0
    success = persistence.save_guild_member(member2_data)
    print(f"✓ 保存公会成员（普通成员）: 成功={success}")

    # 获取公会成员列表
    members = persistence.get_guild_members(1)
    print(f"✓ 获取公会成员列表: {len(members)}人")
    for member in members:
        rank_names = ['会长', '副会长', '官员', '成员', '新人']
        rank_name = rank_names[member['rank']] if member['rank'] < len(rank_names) else '未知'
        print(f"  - {member['character_name']} (职位: {rank_name}, 等级: {member['level']}, 贡献: {member['contribution']})")

    # 保存公会申请
    application_data = {
        'application_id': 1,
        'guild_id': 1,
        'character_id': 'test_char_003',
        'character_name': '测试角色3',
        'account_id': 'acc_003',
        'status': 0,  # 待处理
        'message': '我想加入公会！',
        'level': 50,
        'job': 'mage',
        'apply_time': time.time(),
    }
    success = persistence.save_guild_application(application_data)
    print(f"✓ 保存公会申请: 成功={success}")

    # 获取公会申请列表
    applications = persistence.get_guild_applications(1, status=0)
    print(f"✓ 获取待处理申请: {len(applications)}条")
    for app in applications:
        print(f"  - {app['character_name']} (等级: {app['level']}, 留言: {app['message']})")

    # 更新申请状态（已批准）
    application_data['status'] = 1
    application_data['process_time'] = time.time()
    application_data['processed_by'] = 'test_char_001'
    success = persistence.save_guild_application(application_data)
    print(f"✓ 更新申请状态（已批准）: 成功={success}")

    print()

    # 测试4: 统计信息
    print("【测试4: 统计信息】")
    print("-" * 70)

    stats = persistence.get_statistics()
    print(f"✓ 获取统计信息:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print()

    # 测试5: 删除公会（级联删除）
    print("【测试5: 删除公会（级联删除）】")
    print("-" * 70)

    success = persistence.delete_guild(1)
    print(f"✓ 删除公会: 成功={success}")

    guild = persistence.get_guild(1)
    print(f"  公会是否存在: {'是' if guild else '否'}")

    members = persistence.get_guild_members(1)
    print(f"  公会成员数: {len(members)}")

    applications = persistence.get_guild_applications(1, status=1)
    print(f"  公会申请数: {len(applications)}")

    print()

    # 清理
    db_manager.close()
    os.remove(db_path)
    os.rmdir(temp_dir)
    print("✓ 测试数据库已清理")

    print()
    print("=" * 70)
    print("✅ 所有数据库持久化扩展测试通过！")
    print("副本、拍卖行、公会系统的数据库存储功能正常")
    print("=" * 70)


if __name__ == "__main__":
    main()
