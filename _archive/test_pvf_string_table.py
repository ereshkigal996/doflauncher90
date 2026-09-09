# -*- coding: utf-8 -*-
"""
测试PVF字符串表解析，查找物品真正的中文名称
"""
import sys
import os
import json
import struct

sys.path.insert(0, r"C:\Users\56518\Downloads\DBObject\pip\gmtool")
from pvf_parser import PVFParser

def find_string_table_files(parser):
    """查找字符串表相关文件"""
    print("[1] 查找字符串表相关文件...")
    
    # 查找可能的字符串表文件
    candidates = [
        "stringtable.bin",
        "n_string.lst",
        "string.lst",
        "stringtable.lst",
        "n_stringtable.bin",
    ]
    
    found = []
    for name in candidates:
        raw = parser.read_file_raw(name)
        if raw:
            print(f"  找到: {name} ({len(raw)} 字节)")
            found.append((name, raw))
    
    # 搜索包含string的文件名
    print()
    print("  搜索包含'string'的文件（前20个）:")
    string_files = [f for f in parser.files if 'string' in f['name'].lower() or 'string' in f['path'].lower()]
    for i, f in enumerate(string_files[:20]):
        print(f"    {i+1}. {f['archive_path']} ({f['size']} 字节)")
    
    return found

def parse_string_table_bin(raw):
    """尝试解析stringtable.bin格式"""
    print()
    print("[2] 解析stringtable.bin...")
    
    if not raw or len(raw) < 16:
        print("  文件太小，无法解析")
        return {}
    
    print(f"  文件大小: {len(raw)} 字节")
    print(f"  前32字节(hex): {raw[:32].hex()}")
    print(f"  前32字节(ascii): {raw[:32]}")
    
    # 尝试不同的解析方式
    strings = {}
    
    # 方式1：简单的长度+字符串格式
    try:
        pos = 0
        count = 0
        while pos < len(raw) - 4 and count < 100:
            # 读取4字节长度
            if pos + 4 > len(raw):
                break
            str_len = struct.unpack('<I', raw[pos:pos+4])[0]
            
            if str_len > 0 and str_len < 1000 and pos + 4 + str_len <= len(raw):
                str_data = raw[pos+4:pos+4+str_len]
                try:
                    text = str_data.decode('utf-8')
                    if any('\u4e00' <= c <= '\u9fff' for c in text):
                        strings[count] = text
                        if count < 10:
                            print(f"  [{count}] {text[:50]}")
                except:
                    pass
                pos += 4 + str_len
                count += 1
            else:
                pos += 1
    except Exception as e:
        print(f"  解析失败: {e}")
    
    print(f"  共找到 {len(strings)} 个中文字符串")
    return strings

def parse_n_string_lst(raw):
    """尝试解析n_string.lst格式"""
    print()
    print("[3] 解析n_string.lst...")
    
    if not raw or len(raw) < 16:
        print("  文件太小，无法解析")
        return {}
    
    print(f"  文件大小: {len(raw)} 字节")
    print(f"  前64字节(hex): {raw[:64].hex()}")
    
    # 尝试按行解析
    strings = {}
    try:
        # 尝试UTF-8解码
        text = raw.decode('utf-8', errors='replace')
        lines = text.split('\n')
        print(f"  行数: {len(lines)}")
        print(f"  前10行:")
        for i, line in enumerate(lines[:10]):
            print(f"    {i}: {line[:80]}")
        
        # 解析 name_xxx = 中文名称 格式
        for line in lines:
            line = line.strip()
            if '=' in line and 'name_' in line.lower():
                parts = line.split('=', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip().strip('`').strip("'")
                    if value:
                        strings[key] = value
    except Exception as e:
        print(f"  解析失败: {e}")
    
    print(f"  共解析 {len(strings)} 个名称映射")
    if strings:
        print("  前10个:")
        for i, (k, v) in enumerate(list(strings.items())[:10]):
            print(f"    {k} = {v}")
    
    return strings

def test_item_with_string_table(parser, string_map):
    """使用字符串表测试物品名称解析"""
    print()
    print("[4] 使用字符串表测试物品名称...")
    
    stk_files = parser.find_files_by_extension('.stk')
    
    # 测试前30个物品
    resolved = 0
    unresolved = 0
    
    print(f"  {'序号':>4s}  {'物品ID':>12s}  {'原始name':<25s}  {'解析后名称':<30s}")
    print("  " + "-" * 90)
    
    for i, f in enumerate(stk_files[:30]):
        try:
            content = parser.read_file_text(f['archive_path'])
            
            # 提取[name]标签
            name_marker = '[name]'
            idx = content.find(name_marker)
            raw_name = ''
            if idx >= 0:
                rest = content[idx + len(name_marker):]
                start = rest.find('`')
                if start >= 0:
                    end = rest.find('`', start + 1)
                    if end >= 0:
                        raw_name = rest[start + 1:end].strip()
            
            # 从字符串表查找
            resolved_name = raw_name
            if raw_name.startswith('name_'):
                if raw_name in string_map:
                    resolved_name = string_map[raw_name]
                    resolved += 1
                else:
                    # 尝试去掉前缀查找
                    key = raw_name
                    if key in string_map:
                        resolved_name = string_map[key]
                        resolved += 1
                    else:
                        unresolved += 1
            elif raw_name:
                resolved += 1
            else:
                unresolved += 1
            
            file_id = os.path.splitext(f['name'])[0]
            print(f"  {i+1:4d}  {file_id:>12s}  {raw_name[:25]:<25s}  {resolved_name[:30]:<30s}")
            
        except Exception as e:
            print(f"  {i+1:4d}  错误: {str(e)[:30]}")
    
    print()
    print(f"  成功解析: {resolved}, 未解析: {unresolved}")

def main():
    pvf_path = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf"
    
    print("=" * 70)
    print("PVF字符串表解析测试")
    print("=" * 70)
    print()
    
    # 解析PVF
    print("解析PVF文件...")
    parser = PVFParser(pvf_path)
    parser.load()
    print(f"  文件数: {parser.file_count}")
    print()
    
    # 1. 查找字符串表文件
    found_files = find_string_table_files(parser)
    
    # 2. 解析stringtable.bin
    string_table = {}
    for name, raw in found_files:
        if name == 'stringtable.bin':
            string_table = parse_string_table_bin(raw)
    
    # 3. 解析n_string.lst
    string_map = {}
    for name, raw in found_files:
        if name == 'n_string.lst':
            string_map = parse_n_string_lst(raw)
    
    # 合并字符串映射
    all_map = {}
    all_map.update(string_map)
    
    # 4. 测试物品名称
    test_item_with_string_table(parser, all_map)
    
    # 5. 保存字符串表
    if all_map:
        output_path = r"C:\Users\56518\Downloads\DBObject\pvf_string_table.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_map, f, ensure_ascii=False, indent=2)
        print()
        print(f"字符串表已保存到: {output_path}")
        print(f"共 {len(all_map)} 个条目")
    
    print()
    print("=" * 70)
    print("测试完成！")
    print("=" * 70)

if __name__ == '__main__':
    main()
