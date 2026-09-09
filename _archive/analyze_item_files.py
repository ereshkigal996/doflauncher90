# -*- coding: utf-8 -*-
"""
分析PVF中物品相关文件，找出装备、时装等文件类型
"""
import sys
sys.path.insert(0, r'C:\Users\56518\Downloads\DBObject\pip\gmtool')

from pvf_parser import PVFParser
from collections import Counter
import os

# 加载PVF
pvf_path = r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf'
parser = PVFParser(pvf_path)
parser.load()

print("=" * 70)
print("PVF物品相关文件分析")
print("=" * 70)

# 1. 统计所有扩展名
print("\n--- 所有文件扩展名统计（前30）---")
ext_counter = Counter()
for f in parser.files:
    ext = os.path.splitext(f['name'])[1].lower()
    ext_counter[ext] += 1

for ext, count in ext_counter.most_common(30):
    print(f"  {ext:15s}: {count:8d}")

# 2. 查找物品相关目录
print("\n--- 物品相关目录统计 ---")
item_dirs = ['stackable', 'equipment', 'avatar', 'creature', 'item', 'weapon', 'armor']
dir_counter = Counter()
for f in parser.files:
    path_lower = f['archive_path'].lower().replace('\\', '/')
    for d in item_dirs:
        if f'/{d}/' in path_lower or path_lower.startswith(f'{d}/'):
            dir_counter[d] += 1
            break

for d, count in dir_counter.most_common():
    print(f"  {d:15s}: {count:8d}")

# 3. 查找equipment目录下的文件
print("\n--- equipment目录下的文件扩展名统计 ---")
equip_ext_counter = Counter()
equip_files = []
for f in parser.files:
    path_lower = f['archive_path'].lower().replace('\\', '/')
    if '/equipment/' in path_lower or path_lower.startswith('equipment/'):
        ext = os.path.splitext(f['name'])[1].lower()
        equip_ext_counter[ext] += 1
        if len(equip_files) < 20:
            equip_files.append(f['archive_path'])

for ext, count in equip_ext_counter.most_common():
    print(f"  {ext:15s}: {count:8d}")

print("\n  equipment目录下的文件示例（前20）:")
for p in equip_files:
    print(f"    {p}")

# 4. 查找avatar（时装）目录
print("\n--- avatar（时装）相关文件统计 ---")
avatar_ext_counter = Counter()
avatar_files = []
for f in parser.files:
    path_lower = f['archive_path'].lower().replace('\\', '/')
    if 'avatar' in path_lower:
        ext = os.path.splitext(f['name'])[1].lower()
        avatar_ext_counter[ext] += 1
        if len(avatar_files) < 20:
            avatar_files.append(f['archive_path'])

for ext, count in avatar_ext_counter.most_common():
    print(f"  {ext:15s}: {count:8d}")

print("\n  avatar目录下的文件示例（前20）:")
for p in avatar_files:
    print(f"    {p}")

# 5. 查找.equ文件
print("\n--- .equ文件分析 ---")
equ_files = []
for f in parser.files:
    if f['name'].lower().endswith('.equ'):
        equ_files.append(f)

print(f"  .equ文件总数: {len(equ_files)}")
if equ_files:
    print("\n  .equ文件示例（前20）:")
    for f in equ_files[:20]:
        print(f"    {f['archive_path']}")

# 6. 查找stackable目录下的子目录
print("\n--- stackable目录下的子目录统计（前20）---")
stackable_subdirs = Counter()
for f in parser.files:
    path = f['archive_path'].replace('\\', '/')
    if path.startswith('stackable/'):
        parts = path.split('/')
        if len(parts) >= 2:
            stackable_subdirs[parts[1]] += 1

for d, count in stackable_subdirs.most_common(20):
    print(f"  {d:30s}: {count:6d}")

print("\n" + "=" * 70)
print("分析完成")
print("=" * 70)
