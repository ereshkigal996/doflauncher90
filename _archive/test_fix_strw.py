# -*- coding: utf-8 -*-
"""
测试str_w修复后的物品名称解析效果
"""
import sys
import os
import struct

sys.path.insert(0, r"C:\Users\56518\Downloads\DBObject\pip\gmtool")
from pvf_parser import PVFParser

def test_item_name(parser, item_path):
    """测试物品名称解析"""
    raw = parser.read_file_raw(item_path)
    if not raw:
        print(f"  未找到文件: {item_path}")
        return
    
    line_count = len(raw) // 5
    found_name = False
    
    for idx in range(line_count):
        off = idx * 5
        token_type = raw[off]
        value = struct.unpack('<i', raw[off+1:off+5])[0]
        
        if token_type == 3:
            text = parser._resolve_string(value)
            if text == '[name]':
                found_name = True
                continue
        
        if found_name and token_type == 6:
            name = parser._resolve_string(value)
            print(f"  物品名称: '{name}'")
            print(f"  value: {value} (0x{value:x}), 最低位: {value & 1}")
            return

def main():
    pvf_path = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf"
    
    print("解析PVF文件...")
    parser = PVFParser(pvf_path)
    parser.load()
    
    print()
    print(f"  strA大小: {len(parser.str_a) if parser.str_a else 0}")
    print(f"  strW大小: {len(parser.str_w) if parser.str_w else 0}")
    print()
    
    if parser.str_w:
        print("  str_w前200字节:")
        preview = parser.str_w[:200]
        try:
            text = preview.decode('utf-16-le', errors='replace')
            print(f"    UTF-16-LE: {text[:100]}")
        except:
            pass
        try:
            text = preview.decode('utf-8', errors='replace')
            print(f"    UTF-8: {text[:100]}")
        except:
            pass
        print()
    
    # 测试用户之前提供的物品
    print("=" * 60)
    print("测试物品名称解析")
    print("=" * 60)
    print()
    
    test_items = [
        ("神圣稀有克隆装扮礼盒", "stackable/cash/chn_20140729_randombox/chn_clone_rare_avatarbox_2683816.stk"),
        ("引用格式物品", "stackable/10000001/10000059.stk"),
    ]
    
    for name, path in test_items:
        print(f"[{name}]")
        print(f"  路径: {path}")
        test_item_name(parser, path)
        print()
    
    # 统计有名称的物品数量
    print("=" * 60)
    print("统计物品名称解析情况")
    print("=" * 60)
    print()
    
    stk_files = parser.find_files_by_extension('.stk')
    named_count = 0
    unnamed_count = 0
    
    for i, f in enumerate(stk_files[:1000]):  # 先测试前1000个
        raw = parser.read_file_raw(f['archive_path'])
        if not raw:
            continue
        
        line_count = len(raw) // 5
        found_name = False
        item_name = ""
        
        for idx in range(line_count):
            off = idx * 5
            token_type = raw[off]
            value = struct.unpack('<i', raw[off+1:off+5])[0]
            
            if token_type == 3:
                text = parser._resolve_string(value)
                if text == '[name]':
                    found_name = True
                    continue
            
            if found_name and token_type == 6:
                item_name = parser._resolve_string(value)
                break
        
        if item_name and not item_name.startswith('name_'):
            named_count += 1
        else:
            unnamed_count += 1
    
    print(f"  测试前1000个物品:")
    print(f"    有中文名称: {named_count}")
    print(f"    无名称/引用格式: {unnamed_count}")
    print(f"    成功率: {named_count/10:.1f}%")
    
    print()
    print("测试完成！")

if __name__ == '__main__':
    main()
