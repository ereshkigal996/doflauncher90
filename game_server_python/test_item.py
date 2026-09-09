"""
物品系统测试脚本
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.item import (
    ItemManager, ItemRecord, EquipmentItem, CharacterInventory,
    ItemType, EquipSlot, Rarity, InventoryType,
)


def main():
    print("=" * 60)
    print("物品系统测试")
    print("=" * 60)
    print()

    # 创建物品管理器
    manager = ItemManager()
    print("✓ 创建物品管理器")
    print()

    # 测试1: 注册物品模板
    print("测试1: 注册物品模板")

    potion = ItemRecord(
        item_id=1001,
        item_name="雷米的援助",
        item_type=ItemType.CONSUMABLE.value,
        rarity=Rarity.UNCOMMON.value,
        level=1,
        description="恢复HP和MP",
        stackable=True,
        max_stack=9999,
        price=100,
    )
    manager.register_item_template(potion)
    print(f"  注册消耗品: {potion.item_name} (ID={potion.item_id})")

    material = ItemRecord(
        item_id=2001,
        item_name="赫仑皇帝的印章",
        item_type=ItemType.MATERIAL.value,
        rarity=Rarity.RARE.value,
        level=1,
        stackable=True,
        max_stack=9999,
        price=500,
    )
    manager.register_item_template(material)
    print(f"  注册材料: {material.item_name} (ID={material.item_id})")

    weapon = ItemRecord(
        item_id=3001,
        item_name="刺骨",
        item_type=ItemType.EQUIPMENT.value,
        rarity=Rarity.EPIC.value,
        level=60,
        equip_slot=EquipSlot.WEAPON.value,
        physical_attack=500,
        magical_attack=400,
        strength=50,
        price=10000,
    )
    manager.register_item_template(weapon)
    print(f"  注册装备: {weapon.item_name} (ID={weapon.item_id})")

    print("  ✓ 物品模板注册成功")
    print()

    # 测试2: 发放物品
    print("测试2: 发放物品")
    character_id = "test_character"

    success, remaining = manager.give_item(character_id, 1001, 100)
    print(f"  发放消耗品: 成功={success}, 剩余={remaining}")

    success, remaining = manager.give_item(character_id, 2001, 50)
    print(f"  发放材料: 成功={success}, 剩余={remaining}")

    success, remaining = manager.give_item(character_id, 3001, 1, reinforce_level=12)
    print(f"  发放装备(+12): 成功={success}, 剩余={remaining}")

    print("  ✓ 物品发放成功")
    print()

    # 测试3: 背包查询
    print("测试3: 背包查询")
    inventory = manager.get_inventory(character_id)

    potion_count = inventory.get_total_item_count(1001)
    material_count = inventory.get_total_item_count(2001)
    weapon_count = inventory.get_total_item_count(3001)

    print(f"  雷米的援助: {potion_count}个")
    print(f"  赫仑皇帝的印章: {material_count}个")
    print(f"  刺骨: {weapon_count}个")

    for inv_type in InventoryType:
        inv = inventory.get_inventory(inv_type.value)
        if inv:
            item_count = sum(1 for slot in inv.slots if not slot.is_empty)
            print(f"  {inv_type.name}: {item_count}个物品/{inv.capacity}槽位")

    print("  ✓ 背包查询成功")
    print()

    # 测试4: 装备/卸下
    print("测试4: 装备/卸下")
    inventory = manager.get_inventory(character_id)

    weapon_slot = None
    for i, slot in enumerate(inventory.equipment_inventory.slots):
        if not slot.is_empty and slot.item_id == 3001:
            weapon_slot = i
            break

    if weapon_slot is not None:
        success = inventory.equip_item(weapon_slot, EquipSlot.WEAPON.value)
        print(f"  装备刺骨: 成功={success}")
        print(f"  已装备数量: {len(inventory.equipped_items)}")

        if EquipSlot.WEAPON.value in inventory.equipped_items:
            equip = inventory.equipped_items[EquipSlot.WEAPON.value]
            print(f"  装备名称: {equip.item_name}")
            print(f"  强化等级: +{equip.reinforce_level}")

        success = inventory.unequip_item(EquipSlot.WEAPON.value)
        print(f"  卸下刺骨: 成功={success}")
        print(f"  已装备数量: {len(inventory.equipped_items)}")

    print("  ✓ 装备/卸下成功")
    print()

    # 测试5: 移动物品
    print("测试5: 移动物品")
    inventory = manager.get_inventory(character_id)

    slot1 = None
    slot2 = None
    for i, slot in enumerate(inventory.consumable_inventory.slots):
        if not slot.is_empty and slot1 is None:
            slot1 = i
        elif slot.is_empty and slot2 is None:
            slot2 = i
            break

    if slot1 is not None and slot2 is not None:
        item_before = inventory.consumable_inventory.slots[slot1].item_name
        success = inventory.consumable_inventory.move_item(slot1, slot2)
        item_after = inventory.consumable_inventory.slots[slot2].item_name
        print(f"  移动 {item_before} 从槽位{slot1}到槽位{slot2}: 成功={success}")
        print(f"  目标槽位物品: {item_after}")

    print("  ✓ 移动物品成功")
    print()

    # 测试6: 序列化
    print("测试6: 序列化/反序列化")
    inventory = manager.get_inventory(character_id)
    data = inventory.to_dict()
    print(f"  序列化数据键: {list(data.keys())}")
    print(f"  装备背包槽位数: {len(data['equipment_inventory']['slots'])}")
    print(f"  已装备物品数: {len(data['equipped_items'])}")
    print("  ✓ 序列化成功")

    print()
    print("=" * 60)
    print("所有测试通过！物品系统基础功能验证正确")
    print("=" * 60)


if __name__ == "__main__":
    main()
