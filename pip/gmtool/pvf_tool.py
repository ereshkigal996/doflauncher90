#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PVF解析器工具
用于解析DNF的PVF文件，提取文件列表、物品信息等
"""
import sys
import os
import argparse

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pvf_parser import PVFParser
from gm_tool import extract_item_info_from_pvf, translate_item_type, should_filter_item
import re
import json


def parse_pvf(pvf_path, output_file=None, extract_items=False):
    """解析PVF文件"""
    if not os.path.exists(pvf_path):
        print(f"错误：文件不存在 - {pvf_path}")
        return False
    
    print(f"正在解析PVF文件: {pvf_path}")
    parser = PVFParser(pvf_path)
    
    try:
        parser.load()
    except Exception as e:
        print(f"解析失败: {e}")
        return False
    
    print(f"\n解析完成！")
    print(f"  文件总数: {parser.file_count}")
    print(f"  分组数量: {parser.group_count}")
    print(f"  主体大小: {parser.body_size} 字节 ({parser.body_size/1024/1024:.2f} MB)")
    print(f"  strA (UTF-8) 大小: {len(parser.str_a) if parser.str_a else 0} 字节")
    print(f"  strW (UTF-16) 大小: {len(parser.str_w) if parser.str_w else 0} 字节")
    
    # 统计文件类型
    files = parser.list_files()
    extensions = {}
    for f in files:
        name = f['name']
        if '.' in name:
            ext = name.rsplit('.', 1)[1].lower()
            extensions[ext] = extensions.get(ext, 0) + 1
    
    print(f"\n文件类型统计:")
    for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"  .{ext}: {count} 个")
    
    # 提取物品信息
    if extract_items:
        print(f"\n正在提取物品信息...")
        items = []
        stackable_files = [f for f in files if 'stackable' in f['archive_path'].lower() and f['name'].endswith('.stk')]
        equ_files = [f for f in files if 'equipment/character/' in f['archive_path'].lower() and f['name'].endswith('.equ')]
        
        print(f"  消耗品文件: {len(stackable_files)} 个")
        print(f"  装备文件: {len(equ_files)} 个")
        
        # 处理消耗品
        for idx, f in enumerate(stackable_files):
            if idx % 1000 == 0:
                print(f"  处理消耗品: {idx}/{len(stackable_files)}")
            item_info = extract_item_info_from_pvf(parser, f['archive_path'], f['name'])
            if item_info and not should_filter_item(item_info['name']):
                # 翻译类型
                translated_type = translate_item_type(
                    kind=item_info.get('kind', ''),
                    equipment_type=item_info.get('equipment_type', ''),
                    stackable_type=item_info.get('stackable_type', '')
                )
                item_info['type'] = translated_type
                items.append(item_info)
        
        # 处理装备
        for idx, f in enumerate(equ_files):
            if idx % 1000 == 0:
                print(f"  处理装备: {idx}/{len(equ_files)}")
            item_info = extract_item_info_from_pvf(parser, f['archive_path'], f['name'])
            if item_info and not should_filter_item(item_info['name']):
                # 翻译类型
                translated_type = translate_item_type(
                    kind=item_info.get('kind', 'equipment'),
                    equipment_type=item_info.get('equipment_type', ''),
                    stackable_type=item_info.get('stackable_type', '')
                )
                item_info['type'] = translated_type
                items.append(item_info)
        
        print(f"\n提取物品总数: {len(items)}")
        
        # 保存到文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            print(f"物品信息已保存到: {output_file}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description='PVF解析器工具')
    parser.add_argument('pvf_path', help='PVF文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径（JSON格式）')
    parser.add_argument('--items', action='store_true', help='提取物品信息')
    
    args = parser.parse_args()
    
    if not args.pvf_path:
        parser.print_help()
        return
    
    parse_pvf(args.pvf_path, args.output, args.items)


if __name__ == '__main__':
    main()
