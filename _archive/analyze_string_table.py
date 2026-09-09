# -*- coding: utf-8 -*-
"""
深入分析n_string.lst二进制格式，尝试解析物品名称
"""
import sys
import os
import json
import struct

sys.path.insert(0, r"C:\Users\56518\Downloads\DBObject\pip\gmtool")
from pvf_parser import PVFParser

def analyze_n_string_lst(raw):
    """深入分析n_string.lst二进制格式"""
    print("=" * 70)
    print("n_string.lst 二进制格式分析")
    print("=" * 70)
    print()
    
    print(f"文件大小: {len(raw)} 字节")
    print()
    
    # 完整hex输出
    print("完整hex数据:")
    for i in range(0, len(raw), 16):
        hex_part = ' '.join(f'{b:02x}' for b in raw[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in raw[i:i+16])
        print(f"  {i:04x}: {hex_part:<48s} {ascii_part}")
    
    print()
    
    # 尝试解析为索引表
    print("尝试解析为索引表格式...")
    
    # 前4字节可能是数量
    if len(raw) >= 4:
        count = struct.unpack('<I', raw[0:4])[0]
        print(f"  前4字节作为数量: {count}")
        
        # 接下来可能是条目，每个条目8字节（4字节ID + 4字节偏移）
        pos = 4
        entries = []
        while pos + 8 <= len(raw):
            entry_id = struct.unpack('<I', raw[pos:pos+4])[0]
            entry_offset = struct.unpack('<I', raw[pos+4:pos+8])[0]
            entries.append((entry_id, entry_offset))
            pos += 8
        
        print(f"  解析出 {len(entries)} 个条目")
        print("  前20个条目:")
        for i, (eid, off) in enumerate(entries[:20]):
            print(f"    [{i:2d}] ID={eid:10d} (0x{eid:08x}), Offset={off:10d} (0x{off:08x})")
    
    print()
    
    # 尝试另一种格式：2字节数量 + 条目
    print("尝试2字节数量格式...")
    if len(raw) >= 2:
        count2 = struct.unpack('<H', raw[0:2])[0]
        print(f"  前2字节作为数量: {count2}")
    
    return raw

def search_string_pool(parser):
    """从PVF字符串池中搜索物品名称"""
    print()
    print("=" * 70)
    print("从PVF字符串池搜索物品名称")
    print("=" * 70)
    print()
    
    if not parser.str_a:
        print("  字符串池为空")
        return {}
    
    print(f"  strA大小: {len(parser.str_a)} 字节")
    print()
    
    # 搜索包含"name_"的字符串
    print("搜索包含'name_'的字符串...")
    name_refs = []
    search_pos = 0
    while True:
        idx = parser.str_a.find(b'name_', search_pos)
        if idx < 0:
            break
        # 读取这个字符串（到null结束）
        end = parser.str_a.find(b'\x00', idx)
        if end < 0:
            end = min(idx + 100, len(parser.str_a))
        raw_str = parser.str_a[idx:end]
        try:
            text = raw_str.decode('utf-8', errors='replace')
            name_refs.append((idx, text))
        except:
            pass
        search_pos = idx + 1
        if len(name_refs) >= 50:
            break
    
    print(f"  找到 {len(name_refs)} 个包含'name_'的字符串")
    for i, (pos, text) in enumerate(name_refs[:20]):
        print(f"    [{i:2d}] 偏移={pos:8d}, 内容={text[:60]}")
    
    # 搜索中文字符串
    print()
    print("搜索中文字符串（前30个）...")
    chinese_strings = []
    pos = 0
    while pos < len(parser.str_a) and len(chinese_strings) < 30:
        # 查找中文字符（UTF-8编码的中文字符以0xE4-0xE9开头）
        if 0xE4 <= parser.str_a[pos] <= 0xE9:
            # 尝试读取到null
            end = parser.str_a.find(b'\x00', pos)
            if end < 0:
                end = min(pos + 200, len(parser.str_a))
            raw_str = parser.str_a[pos:end]
            try:
                text = raw_str.decode('utf-8')
                if any('\u4e00' <= c <= '\u9fff' for c in text):
                    chinese_strings.append((pos, text))
            except:
                pass
            pos = end + 1
        else:
            pos += 1
    
    print(f"  找到 {len(chinese_strings)} 个中文字符串")
    for i, (pos, text) in enumerate(chinese_strings[:20]):
        print(f"    [{i:2d}] 偏移={pos:8d}, 内容={text[:50]}")
    
    return {}

def test_specific_item(parser, item_id):
    """测试特定物品的名称"""
    print()
    print("=" * 70)
    print(f"测试特定物品: {item_id}")
    print("=" * 70)
    print()
    
    # 查找物品文件
    stk_files = parser.find_files_by_extension('.stk')
    target_file = None
    for f in stk_files:
        if str(item_id) in f['name']:
            target_file = f
            break
    
    if not target_file:
        print(f"  未找到物品 {item_id}")
        return
    
    print(f"  找到文件: {target_file['archive_path']}")
    print(f"  文件大小: {target_file['size']} 字节")
    print()
    
    # 读取文件内容
    content = parser.read_file_text(target_file['archive_path'])
    if content:
        print("  文件内容（前500字符）:")
        print("  " + "-" * 60)
        print(content[:500])
        print("  " + "-" * 60)

def main():
    pvf_path = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf"
    
    # 解析PVF
    print("解析PVF文件...")
    parser = PVFParser(pvf_path)
    parser.load()
    print(f"  文件数: {parser.file_count}")
    print()
    
    # 1. 分析n_string.lst
    n_string_raw = parser.read_file_raw("n_string.lst")
    if n_string_raw:
        analyze_n_string_lst(n_string_raw)
    
    # 2. 搜索字符串池
    search_string_pool(parser)
    
    # 3. 测试特定物品（用户之前提供的示例）
    test_specific_item(parser, "2683816")
    
    # 4. 测试一个引用格式的物品
    test_specific_item(parser, "10000059")
    
    print()
    print("=" * 70)
    print("分析完成！")
    print("=" * 70)

if __name__ == '__main__':
    main()
