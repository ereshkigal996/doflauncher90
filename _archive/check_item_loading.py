# -*- coding: utf-8 -*-
"""
检查特定物品的加载情况
"""
import sys
import json
import os
sys.path.insert(0, r'C:\Users\56518\Downloads\DBObject\pip\gmtool')

from pvf_parser import PVFParser

# 加载PVF
pvf_path = r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf'
parser = PVFParser(pvf_path)
parser.load()

print("=" * 70)
print("检查特定物品加载情况")
print("=" * 70)

# 1. 从items.json查找"赫仑皇帝的印章"
print("\n--- 1. 从items.json查找'赫仑皇帝的印章' ---")
items_json_path = r'C:\Users\56518\Downloads\DBObject\pip\gmtool\items.json'
if os.path.exists(items_json_path):
    with open(items_json_path, 'r', encoding='utf-8-sig') as f:
        items_list = json.load(f)
    
    print(f"items.json共 {len(items_list)} 个物品")
    
    # 搜索包含"印章"的物品
    seal_items = []
    for item in items_list:
        name = item.get('name', '')
        if '印章' in name or '赫仑' in name or '皇帝' in name:
            seal_items.append(item)
    
    print(f"\n包含'印章'或'赫仑'或'皇帝'的物品: {len(seal_items)} 个")
    for item in seal_items[:20]:
        print(f"  ID: {item.get('id')}, 名称: {item.get('name')}, 类型: {item.get('type')}, 分类: {item.get('category')}")
        print(f"    路径: {item.get('path')}")
else:
    print("items.json不存在")

# 2. 从PVF查找印章相关文件
print("\n--- 2. 从PVF查找印章相关文件 ---")
seal_files = []
for f in parser.files:
    name_lower = f['name'].lower()
    path_lower = f['archive_path'].lower()
    if 'seal' in name_lower or 'stamp' in name_lower or '印章' in path_lower:
        seal_files.append(f)

print(f"PVF中包含'seal'或'stap'的文件: {len(seal_files)} 个")
for f in seal_files[:20]:
    print(f"  {f['archive_path']}")

# 3. 检查stackable目录下所有子目录
print("\n--- 3. stackable目录下所有子目录（前30）---")
stackable_subdirs = {}
for f in parser.files:
    path = f['archive_path'].replace('\\', '/')
    if path.startswith('stackable/'):
        parts = path.split('/')
        if len(parts) >= 2:
            subdir = parts[1]
            if subdir not in stackable_subdirs:
                stackable_subdirs[subdir] = 0
            stackable_subdirs[subdir] += 1

sorted_subdirs = sorted(stackable_subdirs.items(), key=lambda x: x[1], reverse=True)
for d, count in sorted_subdirs[:30]:
    print(f"  {d:30s}: {count:6d}")

# 4. 检查物品ID格式
print("\n--- 4. 检查物品ID格式（前50个.stk文件）---")
stk_count = 0
for f in parser.files:
    if f['name'].lower().endswith('.stk'):
        item_id = os.path.splitext(f['name'])[0]
        # 检查是否是纯数字
        is_numeric = item_id.isdigit()
        if stk_count < 50:
            print(f"  ID: {item_id:40s} 纯数字: {is_numeric}  路径: {f['archive_path']}")
        stk_count += 1

print(f"\n.stk文件总数: {stk_count}")

# 5. 检查.equ文件ID格式
print("\n--- 5. 检查.equ文件ID格式（前30个）---")
equ_count = 0
for f in parser.files:
    if f['name'].lower().endswith('.equ'):
        path = f['archive_path'].replace('\\', '/')
        # 只看角色装备
        if 'equipment/character/' in path or ('character/' in path and 'avatar' in path):
            item_id = os.path.splitext(f['name'])[0]
            is_numeric = item_id.isdigit()
            if equ_count < 30:
                print(f"  ID: {item_id:20s} 纯数字: {is_numeric}  路径: {f['archive_path']}")
            equ_count += 1

print(f"\n角色相关.equ文件总数: {equ_count}")

# 6. 搜索特定ID的物品
print("\n--- 6. 搜索特定ID的物品（印章相关ID）---")
# 赫仑皇帝的印章通常ID是 10000039 或类似
test_ids = ['10000039', '10000040', '10000041', '10094886', '490701780']
for test_id in test_ids:
    # 在PVF中查找
    found_in_pvf = False
    for f in parser.files:
        if f['name'].startswith(test_id):
            print(f"  PVF中找到ID {test_id}: {f['archive_path']}")
            found_in_pvf = True
            break
    if not found_in_pvf:
        print(f"  PVF中未找到ID {test_id}")
    
    # 在items.json中查找
    found_in_json = False
    for item in items_list:
        if str(item.get('id')) == test_id:
            print(f"    items.json中: {item.get('name')}")
            found_in_json = True
            break
    if not found_in_json:
        print(f"    items.json中未找到")

print("\n" + "=" * 70)
print("检查完成")
print("=" * 70)
