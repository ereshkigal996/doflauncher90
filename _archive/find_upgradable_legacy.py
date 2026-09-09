# -*- coding: utf-8 -*-
"""
查找使用特定消耗品类型的物品
"""
import sys
import os
import struct

sys.path.insert(0, r"C:\Users\56518\Downloads\DBObject\pip\gmtool")
from pvf_parser import PVFParser
from gm_tool import extract_item_name_from_pvf

def find_items_by_stackable_type(parser, target_type):
    """查找使用特定消耗品类型的物品"""
    print(f"查找消耗品类型为 '{target_type}' 的物品...")
    print()
    
    stk_files = parser.find_files_by_extension('.stk')
    print(f"共 {len(stk_files)} 个.stk文件")
    print()
    
    found_items = []
    
    for idx, file_info in enumerate(stk_files):
        if idx % 10000 == 0:
            print(f"  扫描进度: {idx}/{len(stk_files)}")
        
        archive_path = file_info['archive_path']
        raw = parser.read_file_raw(archive_path)
        if not raw or len(raw) < 5:
            continue
        
        line_count = len(raw) // 5
        current_tag = None
        item_type = None
        item_name = None
        
        for i in range(line_count):
            off = i * 5
            token_type = raw[off]
            value = struct.unpack('<i', raw[off+1:off+5])[0]
            
            if token_type == 3:
                text = parser._resolve_string(value)
                if text:
                    current_tag = text.strip('[]')
                    
            elif token_type == 6 and current_tag:
                text = parser._resolve_string(value)
                if text:
                    if current_tag == 'stackable type':
                        item_type = text
                    elif current_tag == 'name' and not item_name:
                        item_name = text
                current_tag = None
        
        if item_type == target_type:
            # 尝试获取物品名称
            if not item_name:
                item_name = extract_item_name_from_pvf(parser, archive_path)
            
            found_items.append({
                'path': archive_path,
                'name': item_name if item_name else '(未找到名称)',
                'file_name': file_info['name'],
            })
    
    print()
    print("=" * 70)
    print(f"查找结果：共找到 {len(found_items)} 个类型为 '{target_type}' 的物品")
    print("=" * 70)
    print()
    
    if found_items:
        # 显示前50个
        display_count = min(50, len(found_items))
        print(f"显示前 {display_count} 个：")
        print()
        
        for i, item in enumerate(found_items[:display_count]):
            print(f"  [{i+1:3d}] {item['name']}")
            print(f"        路径: {item['path']}")
            print(f"        文件: {item['file_name']}")
            print()
        
        if len(found_items) > 50:
            print(f"  ... 还有 {len(found_items) - 50} 个物品未显示")
            print()
        
        # 统计文件名中的ID范围
        print("物品ID统计：")
        ids = []
        for item in found_items:
            # 尝试从文件名提取ID
            base_name = os.path.splitext(item['file_name'])[0]
            if base_name.isdigit():
                ids.append(int(base_name))
        
        if ids:
            print(f"  ID范围: {min(ids)} - {max(ids)}")
            print(f"  纯数字ID物品数: {len(ids)}")
    else:
        print("  未找到匹配的物品")
    
    return found_items

def main():
    pvf_path = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf"
    
    print("加载PVF解析器...")
    parser = PVFParser(pvf_path)
    parser.load()
    
    print(f"PVF加载成功！")
    print()
    
    # 查找 [upgradable legacy] 类型的物品
    target_type = '[upgradable legacy]'
    found_items = find_items_by_stackable_type(parser, target_type)
    
    print()
    print("查找完成！")

if __name__ == '__main__':
    main()
