# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'C:\Users\56518\Downloads\DBObject\pip\gmtool')

# 测试导入和函数
from gm_tool import (
    load_items_from_pvf, 
    extract_item_info_from_pvf, 
    has_chinese_name,
    should_filter_item,
    FILTERED_STACKABLE_TYPES
)

# 测试should_filter_item函数
test_cases = [
    # (名称, 期望被过滤)
    ('神圣稀有克隆装扮礼盒', False),      # 正常中文名称
    ('DPL Select Box 1', True),           # 无中文名称
    ('15lv', True),                        # 无中文名称
    ('dummy item', True),                  # 无中文名称
    ('赫仑皇帝的印章', False),             # 正常中文名称
    ('', True),                            # 空名称
    (None, True),                          # None
    ('((后续确认', True),                  # ((开头 + 后续确认
    ('后续确认', True),                    # 包含后续确认
    ('((测试物品', True),                  # ((开头
    ('((abc', True),                       # ((开头 + 无中文
    ('正常物品((测试', False),             # 包含((但不在开头，且有中文
]

print('测试should_filter_item函数:')
all_pass = True
for name, expected in test_cases:
    result = should_filter_item(name)
    status = 'PASS' if result == expected else 'FAIL'
    if result != expected:
        all_pass = False
    print(f'  [{status}] should_filter_item("{name}") = {result} (期望: {expected})')

print()
print(f'所有测试通过: {all_pass}')
print(f'过滤类型数量: {len(FILTERED_STACKABLE_TYPES)}')
print()
print('代码语法验证完成！')
