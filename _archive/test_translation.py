# -*- coding: utf-8 -*-
"""
验证新增的翻译映射表
"""
import sys
sys.path.insert(0, r"C:\Users\56518\Downloads\DBObject\pip\gmtool")

from gm_tool import (
    EQUIP_TYPE_MAP, KIND_MAP, SOURCE_MAP, 
    STACKABLE_TYPE_MAP, ATTACH_TYPE_MAP,
    translate_item_type, translate_attach_type, translate_source
)

print("=" * 70)
print("翻译映射表统计")
print("=" * 70)
print(f"  装备类型 EQUIP_TYPE_MAP: {len(EQUIP_TYPE_MAP)} 个")
print(f"  物品种类 KIND_MAP: {len(KIND_MAP)} 个")
print(f"  消耗品类型 STACKABLE_TYPE_MAP: {len(STACKABLE_TYPE_MAP)} 个")
print(f"  附加类型 ATTACH_TYPE_MAP: {len(ATTACH_TYPE_MAP)} 个")
print(f"  物品来源 SOURCE_MAP: {len(SOURCE_MAP)} 个")
print(f"  总计: {len(EQUIP_TYPE_MAP) + len(KIND_MAP) + len(STACKABLE_TYPE_MAP) + len(ATTACH_TYPE_MAP) + len(SOURCE_MAP)} 个")
print()

print("=" * 70)
print("装备类型翻译测试（新增）")
print("=" * 70)
test_equip = [
    ('[skill weapon]', '技能武器'),
    ('[skill coat]', '技能上衣'),
    ('[weapon]', '武器'),
    ('[charm]', '快捷栏装备'),
]
for eng, expected in test_equip:
    result = translate_item_type(equipment_type=eng)
    status = "✓" if result == expected else "✗"
    print(f"  {status} {eng:<25s} -> {result:<15s} (期望: {expected})")

print()
print("=" * 70)
print("消耗品类型翻译测试")
print("=" * 70)
test_stack = [
    ('[recipe]', '设计图'),
    ('[material expert job]', '副职业材料'),
    ('[usable cera package]', '可用点券礼包'),
    ('[booster selection]', '自选礼盒'),
    ('[upgradable legacy]', '传承'),
    ('[legacy]', '传承'),
    ('[material]', '材料'),
    ('[waste]', '杂物'),
    ('[enchant waste]', '附魔材料'),
    ('[avatar emblem]', '装扮徽章'),
    ('[quest]', '任务物品'),
    ('[dye]', '染色剂'),
    ('[coupon]', '优惠券'),
    ('[contract]', '契约'),
    ('[booster]', '礼盒'),
]
for eng, expected in test_stack:
    result = translate_item_type(stackable_type=eng)
    status = "✓" if result == expected else "✗"
    print(f"  {status} {eng:<30s} -> {result:<15s} (期望: {expected})")

print()
print("=" * 70)
print("附加类型翻译测试")
print("=" * 70)
test_attach = [
    ('[trade]', '可交易'),
    ('[account]', '账号绑定'),
    ('[free]', '无法交易'),
    ('[sealing]', '可密封'),
    ('[trade delete]', '交易后删除'),
    ('[trade limit]', '交易限制'),
]
for eng, expected in test_attach:
    result = translate_attach_type(eng)
    status = "✓" if result == expected else "✗"
    print(f"  {status} {eng:<25s} -> {result:<15s} (期望: {expected})")

print()
print("=" * 70)
print("综合测试（kind + equipment_type + stackable_type优先级）")
print("=" * 70)
# equipment_type优先级最高
result = translate_item_type(kind='stackable', equipment_type='[weapon]', stackable_type='[recipe]')
print(f"  equipment_type优先: kind=stackable, equip=[weapon], stack=[recipe] -> {result}")

# stackable_type次之
result = translate_item_type(kind='stackable', equipment_type='', stackable_type='[recipe]')
print(f"  stackable_type次之: kind=stackable, equip=空, stack=[recipe] -> {result}")

# kind最后
result = translate_item_type(kind='stackable', equipment_type='', stackable_type='')
print(f"  kind最后: kind=stackable, equip=空, stack=空 -> {result}")

print()
print("验证完成！")
