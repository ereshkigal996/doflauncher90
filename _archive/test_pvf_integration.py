# -*- coding: utf-8 -*-
"""
测试GM工具中PVF物品加载功能
"""
import sys
import os

# 添加GM工具目录到路径
sys.path.insert(0, r'C:\Users\56518\Downloads\DBObject\pip\gmtool')

print("=" * 60)
print("测试PVF物品加载功能")
print("=" * 60)

# 导入GM工具中的PVF加载功能
try:
    from gm_tool import load_items_from_pvf, load_pvf_parser, get_pvf_path, PVF_PARSER_AVAILABLE
    print("✓ PVF加载功能导入成功")
    print(f"  PVF_PARSER_AVAILABLE: {PVF_PARSER_AVAILABLE}")
except Exception as e:
    print(f"✗ 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("--- 测试1: 获取PVF文件路径 ---")
pvf_path = get_pvf_path()
print(f"PVF路径: {pvf_path}")
if pvf_path and os.path.exists(pvf_path):
    print(f"✓ 文件存在，大小: {os.path.getsize(pvf_path)/1024/1024:.2f} MB")
else:
    print("✗ 文件不存在")

print()
print("--- 测试2: 加载PVF解析器 ---")
parser = load_pvf_parser()
if parser:
    print(f"✓ PVF解析器加载成功")
    print(f"  格式: {parser.format}")
    print(f"  文件数量: {parser.file_count}")
    print(f"  数据块数量: {parser.group_count}")
else:
    print("✗ PVF解析器加载失败")

print()
print("--- 测试3: 从PVF加载物品列表 ---")
items = load_items_from_pvf()
if items:
    print(f"✓ 物品列表加载成功，共 {len(items)} 个物品")
    print()
    print("前20个物品:")
    for i, item in enumerate(items[:20]):
        print(f"  {i+1:2d}. ID: {item['id']:12s} 名称: {item['name']:20s} 类型: {item['type']:15s} 分类: {item['category']}")
    
    print()
    print("按分类统计:")
    category_count = {}
    for item in items:
        cat = item.get('category', '未知')
        category_count[cat] = category_count.get(cat, 0) + 1
    for cat, count in sorted(category_count.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat:10s}: {count:6d}")
    
    print()
    print("按类型统计（前10）:")
    type_count = {}
    for item in items:
        t = item.get('type', '未知')
        if t:
            type_count[t] = type_count.get(t, 0) + 1
    for t, count in sorted(type_count.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {t:20s}: {count:6d}")
else:
    print("✗ 物品列表加载失败")

print()
print("=" * 60)
print("测试完成")
print("=" * 60)
