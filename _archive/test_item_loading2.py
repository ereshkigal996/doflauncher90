# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'C:\Users\56518\Downloads\DBObject\pip\gmtool')
from gm_tool import load_items_from_pvf
from collections import Counter

print('正在加载物品列表...')
items = load_items_from_pvf()

if items:
    print(f'\n物品总数: {len(items)}')
    
    # 搜索赫仑皇帝的印章
    print('\n--- 搜索赫仑皇帝的印章 ---')
    found = False
    for item in items:
        name = item.get('name', '')
        if '赫仑' in name or '皇帝的印章' in name:
            print(f'  ID: {item["id"]}, 名称: {item["name"]}, 类型: {item["type"]}, 分类: {item["category"]}')
            print(f'    路径: {item["path"]}')
            found = True
    if not found:
        print('  未找到！')
    
    # 搜索印章相关
    print('\n--- 搜索印章相关物品（前10个）---')
    count = 0
    for item in items:
        name = item.get('name', '')
        if '印章' in name:
            print(f'  ID: {item["id"]:12s}, 名称: {item["name"]:20s}, 分类: {item["category"]}')
            count += 1
            if count >= 10:
                break
    
    # 分类统计
    print('\n--- 分类统计 ---')
    cat_counter = Counter()
    for item in items:
        cat = item.get('category', '未知')
        cat_counter[cat] += 1
    for cat, count in cat_counter.most_common(10):
        print(f'  {cat:10s}: {count:6d}')
    
    # 检查消耗品
    print('\n--- 消耗品示例（前10个）---')
    count = 0
    for item in items:
        if item.get('category') == '消耗品' or item.get('kind') == 'stackable':
            print(f'  ID: {item["id"]:12s}, 名称: {item["name"]:20s}, 类型: {item["type"]}')
            count += 1
            if count >= 10:
                break
    
    # 检查装备
    print('\n--- 装备示例（前10个）---')
    count = 0
    for item in items:
        if item.get('category') == '装备' or item.get('kind') == 'equipment':
            print(f'  ID: {item["id"]:12s}, 名称: {item["name"]:20s}, 类型: {item["type"]}')
            count += 1
            if count >= 10:
                break
else:
    print('物品加载失败！')
