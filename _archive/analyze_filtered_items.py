# -*- coding: utf-8 -*-
"""
分析PVF中需要过滤的物品：
1. 名称为"后续确认"的物品
2. 名称以"name_"开头的物品（引用格式）
3. 无法翻译的物品（无中文name或返回乱码）
"""
import sys
import os
import struct
import re

sys.path.insert(0, r"C:\Users\56518\Downloads\DBObject\pip\gmtool")
from pvf_parser import PVFParser
from gm_tool import extract_item_info_from_pvf, FILTERED_STACKABLE_TYPES

def is_chinese(text):
    """检查文本是否包含中文字符"""
    if not text:
        return False
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False

def is_garbled(text):
    """检查文本是否为乱码（包含大量特殊字符或不可打印字符）"""
    if not text:
        return True
    # 统计可打印字符比例
    printable_count = sum(1 for ch in text if ch.isprintable())
    if printable_count / len(text) < 0.5:
        return True
    # 检查是否包含大量替换字符
    if text.count('�') > len(text) * 0.1:
        return True
    return False

def analyze_items(parser):
    """分析所有物品，整理需要过滤的清单"""
    print("=" * 80)
    print("分析PVF中需要过滤的物品")
    print("=" * 80)
    print()
    
    # 查找所有.stk和.equ文件
    stk_files = parser.find_files_by_extension('.stk')
    equ_files = parser.find_files_by_extension('.equ')
    all_files = stk_files + equ_files
    
    print(f".stk文件: {len(stk_files)} 个")
    print(f".equ文件: {len(equ_files)} 个")
    print(f"总计: {len(all_files)} 个")
    print()
    
    # 分类统计
    items_followup_confirm = []      # 后续确认
    items_name_reference = []         # name_开头的引用格式
    items_no_chinese = []             # 无中文名称
    items_garbled = []                # 乱码
    items_filtered_type = []          # 已过滤的类型
    items_normal = []                 # 正常物品
    
    total = len(all_files)
    
    for idx, file_info in enumerate(all_files):
        if idx % 20000 == 0:
            print(f"  分析进度: {idx}/{total}")
        
        archive_path = file_info['archive_path']
        file_name = file_info['name']
        
        # 只处理角色装备和时装（排除怪物装备等）
        path_lower = archive_path.lower().replace('\\', '/')
        is_character_equip = False
        if path_lower.startswith('stackable/'):
            is_character_equip = True
        elif 'equipment/character/' in path_lower:
            is_character_equip = True
        elif '/avatar/' in path_lower and 'character/' in path_lower:
            is_character_equip = True
        
        if not is_character_equip:
            continue
        
        # 从PVF解析物品信息
        item_info = extract_item_info_from_pvf(parser, archive_path, file_name)
        if not item_info:
            continue
        
        item_name = item_info['name']
        item_type = item_info['type']
        kind = item_info['kind']
        
        # 检查是否为已过滤的类型
        type_for_check = item_type if item_type.startswith('[') else f'[{item_type}]'
        if kind == 'stackable' and type_for_check in FILTERED_STACKABLE_TYPES:
            items_filtered_type.append({
                'name': item_name,
                'path': archive_path,
                'type': item_type,
            })
            continue
        
        # 分类
        if item_name == '后续确认':
            items_followup_confirm.append({
                'name': item_name,
                'path': archive_path,
                'type': item_type,
            })
        elif item_name.startswith('name_'):
            items_name_reference.append({
                'name': item_name,
                'path': archive_path,
                'type': item_type,
            })
        elif is_garbled(item_name):
            items_garbled.append({
                'name': item_name,
                'path': archive_path,
                'type': item_type,
            })
        elif not is_chinese(item_name):
            items_no_chinese.append({
                'name': item_name,
                'path': archive_path,
                'type': item_type,
            })
        else:
            items_normal.append({
                'name': item_name,
                'path': archive_path,
                'type': item_type,
            })
    
    print()
    print("=" * 80)
    print("分析结果统计")
    print("=" * 80)
    print()
    print(f"  正常物品（有中文名称）: {len(items_normal)} 个")
    print(f"  已过滤类型（不可用道具）: {len(items_filtered_type)} 个")
    print(f"  '后续确认'物品: {len(items_followup_confirm)} 个")
    print(f"  'name_'引用格式物品: {len(items_name_reference)} 个")
    print(f"  无中文名称物品: {len(items_no_chinese)} 个")
    print(f"  乱码物品: {len(items_garbled)} 个")
    print()
    
    total_filtered = (len(items_followup_confirm) + len(items_name_reference) + 
                      len(items_no_chinese) + len(items_garbled) + len(items_filtered_type))
    total_analyzed = len(items_normal) + total_filtered
    print(f"  总计分析: {total_analyzed} 个")
    print(f"  需要过滤: {total_filtered} 个 ({total_filtered/total_analyzed*100:.1f}%)")
    print(f"  保留正常: {len(items_normal)} 个 ({len(items_normal)/total_analyzed*100:.1f}%)")
    print()
    
    # 显示各类物品示例
    print("=" * 80)
    print("各类物品示例（前20个）")
    print("=" * 80)
    
    categories = [
        ("'后续确认'物品", items_followup_confirm),
        ("'name_'引用格式物品", items_name_reference),
        ("无中文名称物品", items_no_chinese),
        ("乱码物品", items_garbled),
    ]
    
    for cat_name, cat_items in categories:
        print()
        print(f"【{cat_name}】共 {len(cat_items)} 个")
        if cat_items:
            for i, item in enumerate(cat_items[:20]):
                name_display = item['name'][:50] if item['name'] else '(空)'
                print(f"  [{i+1:2d}] {name_display:<50s} | {item['path']}")
            if len(cat_items) > 20:
                print(f"  ... 还有 {len(cat_items) - 20} 个")
    
    # 保存完整清单到文件
    print()
    print("=" * 80)
    print("保存完整清单到文件")
    print("=" * 80)
    
    output_file = r"C:\Users\56518\Downloads\DBObject\filtered_items_list.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("PVF物品过滤清单\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"正常物品（有中文名称）: {len(items_normal)} 个\n")
        f.write(f"已过滤类型（不可用道具）: {len(items_filtered_type)} 个\n")
        f.write(f"'后续确认'物品: {len(items_followup_confirm)} 个\n")
        f.write(f"'name_'引用格式物品: {len(items_name_reference)} 个\n")
        f.write(f"无中文名称物品: {len(items_no_chinese)} 个\n")
        f.write(f"乱码物品: {len(items_garbled)} 个\n\n")
        
        categories = [
            ("'后续确认'物品", items_followup_confirm),
            ("'name_'引用格式物品", items_name_reference),
            ("无中文名称物品", items_no_chinese),
            ("乱码物品", items_garbled),
            ("已过滤类型（不可用道具）", items_filtered_type),
        ]
        
        for cat_name, cat_items in categories:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"【{cat_name}】共 {len(cat_items)} 个\n")
            f.write("=" * 80 + "\n\n")
            for i, item in enumerate(cat_items):
                f.write(f"[{i+1:4d}] {item['name']}\n")
                f.write(f"       路径: {item['path']}\n")
                f.write(f"       类型: {item['type']}\n\n")
    
    print(f"完整清单已保存到: {output_file}")
    print()
    print("分析完成！")

def main():
    pvf_path = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf"
    
    print("加载PVF解析器...")
    parser = PVFParser(pvf_path)
    parser.load()
    
    print(f"PVF加载成功！")
    print()
    
    analyze_items(parser)

if __name__ == '__main__':
    main()
