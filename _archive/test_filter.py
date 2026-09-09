# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'C:\Users\56518\Downloads\DBObject\pip\gmtool')

# 测试导入和函数
from gm_tool import (
    load_items_from_pvf, 
    extract_item_info_from_pvf, 
    has_chinese_name,
    FILTERED_STACKABLE_TYPES
)

# 测试has_chinese_name函数
test_cases = [
    ('神圣稀有克隆装扮礼盒', True),
    ('DPL Select Box 1', False),
    ('15lv', False),
    ('dummy item', False),
    ('赫仑皇帝的印章', True),
    ('', False),
    (None, False),
]

print('测试has_chinese_name函数:')
all_pass = True
for name, expected in test_cases:
    result = has_chinese_name(name)
    status = 'PASS' if result == expected else 'FAIL'
    if result != expected:
        all_pass = False
    print(f'  [{status}] has_chinese_name("{name}") = {result} (期望: {expected})')

print()
print(f'所有测试通过: {all_pass}')
print(f'过滤类型数量: {len(FILTERED_STACKABLE_TYPES)}')
print()
print('代码语法验证完成！')
