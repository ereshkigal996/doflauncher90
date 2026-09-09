# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'C:\Users\56518\Downloads\DBObject\pip\gmtool')

# 测试导入和函数
from gm_tool import (
    load_items_from_pvf, 
    extract_item_info_from_pvf, 
    has_chinese_name,
    should_filter_item,
    translate_item_type,
    FILTERED_STACKABLE_TYPES,
    STACKABLE_TYPE_MAP,
    EQUIP_TYPE_MAP
)

# 测试translate_item_type函数
test_cases = [
    # (kind, equipment_type, stackable_type, 期望翻译)
    ('stackable', '', '[material]', '材料'),
    ('stackable', '', '[booster]', '礼盒'),
    ('stackable', '', '[quest]', '任务物品'),
    ('equipment', '[weapon]', '', '武器'),
    ('equipment', '[coat]', '', '上衣'),
    ('stackable', '', '[nonexistent]', 'nonexistent'),  # 未匹配的去掉括号
]

print('测试translate_item_type函数:')
all_pass = True
for kind, eq_type, st_type, expected in test_cases:
    result = translate_item_type(kind=kind, equipment_type=eq_type, stackable_type=st_type)
    status = 'PASS' if result == expected else 'FAIL'
    if result != expected:
        all_pass = False
    print(f'  [{status}] translate_item_type(kind={kind}, eq={eq_type}, st={st_type}) = "{result}" (期望: "{expected}")')

print()
print(f'所有测试通过: {all_pass}')
print(f'消耗品类型翻译数量: {len(STACKABLE_TYPE_MAP)}')
print(f'装备类型翻译数量: {len(EQUIP_TYPE_MAP)}')
print()
print('代码语法验证完成！')
