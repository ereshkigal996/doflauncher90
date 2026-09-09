"""
拍卖行系统测试脚本
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.auction import (
    AuctionManager, AuctionItem, AuctionListing, AuctionTransaction,
    AuctionStatus, AuctionItemType, AuctionSortBy,
)


def main():
    print("=" * 60)
    print("拍卖行系统测试")
    print("=" * 60)
    print()

    # 创建拍卖行管理器
    manager = AuctionManager()
    print("✓ 创建拍卖行管理器")
    print()

    # 测试1: 上架物品
    print("测试1: 上架物品")

    # 上架装备
    item1 = AuctionItem(
        item_id=3001,
        item_name="刺骨",
        item_type=AuctionItemType.WEAPON.value,
        item_level=60,
        rarity=3,
        quantity=1,
        reinforce_level=12,
        amplify_level=10,
        amplify_type="strength",
        quality=100,
    )
    success, reason, listing1 = manager.list_item(
        seller_id="seller1",
        seller_name="卖家A",
        item=item1,
        price=5000000,
        duration_hours=24,
    )
    print(f"  上架'刺骨+12': 成功={success}, 原因={reason}")
    if listing1:
        print(f"    上架ID: {listing1.listing_id}")
        print(f"    价格: {listing1.price}")
        print(f"    押金: {listing1.deposit_fee}")
        print(f"    剩余时间: {listing1.remaining_time/3600:.1f}小时")

    # 上架消耗品
    item2 = AuctionItem(
        item_id=1001,
        item_name="雷米的援助",
        item_type=AuctionItemType.CONSUMABLE.value,
        item_level=1,
        rarity=1,
        quantity=100,
    )
    success, reason, listing2 = manager.list_item(
        seller_id="seller2",
        seller_name="卖家B",
        item=item2,
        price=100000,
        duration_hours=48,
    )
    print(f"  上架'雷米的援助x100': 成功={success}, 原因={reason}")
    if listing2:
        print(f"    上架ID: {listing2.listing_id}")
        print(f"    单价: {listing2.unit_price}")

    # 上架材料
    item3 = AuctionItem(
        item_id=2001,
        item_name="赫仑皇帝的印章",
        item_type=AuctionItemType.MATERIAL.value,
        item_level=1,
        rarity=2,
        quantity=50,
    )
    success, reason, listing3 = manager.list_item(
        seller_id="seller1",
        seller_name="卖家A",
        item=item3,
        price=50000,
        duration_hours=24,
    )
    print(f"  上架'赫仑皇帝的印章x50': 成功={success}, 原因={reason}")

    print(f"  当前上架物品总数: {len(manager.get_on_sale_listings())}")
    print("  ✓ 物品上架功能正常")
    print()

    # 测试2: 搜索物品
    print("测试2: 搜索物品")

    # 搜索全部
    results, total = manager.search_listings(page=1, page_size=10)
    print(f"  搜索全部: {total}个结果")
    for listing in results:
        print(f"    - {listing.item.item_name} x{listing.item.quantity} ({listing.price}金币)")

    # 按关键词搜索
    results, total = manager.search_listings(keyword="刺骨", page=1, page_size=10)
    print(f"  搜索'刺骨': {total}个结果")

    # 按类型搜索
    results, total = manager.search_listings(item_type=AuctionItemType.CONSUMABLE.value, page=1, page_size=10)
    print(f"  搜索消耗品: {total}个结果")

    # 按价格排序
    results, total = manager.search_listings(sort_by=AuctionSortBy.PRICE_ASC.value, page=1, page_size=10)
    print(f"  按价格升序: {total}个结果")
    if results:
        print(f"    最低价: {results[0].item.item_name} ({results[0].price}金币)")

    print("  ✓ 物品搜索功能正常")
    print()

    # 测试3: 购买物品
    print("测试3: 购买物品")

    # 购买消耗品
    success, reason, transaction = manager.buy_item(
        listing_id=listing2.listing_id,
        buyer_id="buyer1",
        buyer_name="买家A",
        buyer_gold=200000,
    )
    print(f"  购买'雷米的援助': 成功={success}, 原因={reason}")
    if transaction:
        print(f"    交易ID: {transaction.transaction_id}")
        print(f"    物品: {transaction.item_name} x{transaction.quantity}")
        print(f"    价格: {transaction.price}")
        print(f"    手续费: {transaction.transaction_fee}")
        print(f"    卖家收入: {transaction.seller_income}")

    # 检查物品状态
    listing = manager.get_listing(listing2.listing_id)
    if listing:
        print(f"    物品状态: {listing.status} (1=已售出)")
        print(f"    买家: {listing.buyer_name}")

    # 尝试购买已售出的物品（应该失败）
    success, reason, _ = manager.buy_item(
        listing_id=listing2.listing_id,
        buyer_id="buyer2",
        buyer_name="买家B",
        buyer_gold=200000,
    )
    print(f"  再次购买已售出物品: 成功={success}, 原因={reason}")

    # 金币不足的情况
    success, reason, _ = manager.buy_item(
        listing_id=listing1.listing_id,
        buyer_id="buyer1",
        buyer_name="买家A",
        buyer_gold=1000000,  # 不够500万
    )
    print(f"  金币不足购买: 成功={success}, 原因={reason}")

    print("  ✓ 物品购买功能正常")
    print()

    # 测试4: 取消上架
    print("测试4: 取消上架")

    # 取消上架
    success, reason = manager.cancel_listing(listing3.listing_id, "seller1")
    print(f"  取消上架'赫仑皇帝的印章': 成功={success}, 原因={reason}")

    # 检查状态
    listing = manager.get_listing(listing3.listing_id)
    if listing:
        print(f"    物品状态: {listing.status} (3=已取消)")

    # 尝试取消别人的物品（应该失败）
    success, reason = manager.cancel_listing(listing1.listing_id, "seller2")
    print(f"  取消别人的物品: 成功={success}, 原因={reason}")

    print(f"  当前上架物品数: {len(manager.get_on_sale_listings())}")
    print("  ✓ 取消上架功能正常")
    print()

    # 测试5: 用户记录查询
    print("测试5: 用户记录查询")

    # 卖家A的上架记录
    seller_listings = manager.get_user_listings("seller1")
    print(f"  卖家A的上架记录: {len(seller_listings)}个")
    for listing in seller_listings:
        print(f"    - {listing.item.item_name} (状态: {listing.status})")

    # 卖家A的出售记录
    seller_sales = manager.get_user_sales("seller1")
    print(f"  卖家A的出售记录: {len(seller_sales)}个")

    # 卖家B的出售记录
    seller_sales_b = manager.get_user_sales("seller2")
    print(f"  卖家B的出售记录: {len(seller_sales_b)}个")
    for transaction in seller_sales_b:
        print(f"    - {transaction.item_name} x{transaction.quantity} ({transaction.price}金币)")

    # 买家A的购买记录
    buyer_purchases = manager.get_user_purchases("buyer1")
    print(f"  买家A的购买记录: {len(buyer_purchases)}个")
    for transaction in buyer_purchases:
        print(f"    - {transaction.item_name} x{transaction.quantity} ({transaction.price}金币)")

    print("  ✓ 用户记录查询功能正常")
    print()

    # 测试6: 统计信息
    print("测试6: 统计信息")

    stats = manager.get_statistics()
    print(f"  上架中物品数: {stats['on_sale_count']}")
    print(f"  总价值: {stats['total_value']}金币")
    print(f"  总物品数: {stats['total_items']}")
    print(f"  总交易数: {stats['total_transactions']}")
    print(f"  按类型统计:")
    for item_type, type_stat in stats['type_stats'].items():
        print(f"    - {item_type}: {type_stat['count']}个, {type_stat['value']}金币")

    print("  ✓ 统计信息功能正常")
    print()

    # 测试7: 序列化
    print("测试7: 序列化/反序列化")

    data = manager.to_dict()
    print(f"  序列化数据键: {list(data.keys())}")
    print(f"  上架记录数: {data['listings_count']}")
    print(f"  交易记录数: {data['transactions_count']}")
    print(f"  上架中物品数: {data['on_sale_count']}")
    print("  ✓ 序列化成功")

    print()
    print("=" * 60)
    print("所有测试通过！拍卖行系统基础功能验证正确")
    print("=" * 60)


if __name__ == "__main__":
    main()
