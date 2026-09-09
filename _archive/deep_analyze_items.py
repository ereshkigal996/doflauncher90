# -*- coding: utf-8 -*-
"""
深度分析物品文件的原始二进制内容和解码方式
"""
import sys
import os
import json
import struct

sys.path.insert(0, r"C:\Users\56518\Downloads\DBObject\pip\gmtool")
from pvf_parser import PVFParser

def analyze_item_raw(parser, item_path):
    """分析物品文件的原始二进制内容"""
    print(f"\n{'='*70}")
    print(f"分析物品文件: {item_path}")
    print(f"{'='*70}\n")
    
    # 读取原始数据
    raw = parser.read_file_raw(item_path)
    if not raw:
        print("  未找到文件")
        return
    
    print(f"  文件大小: {len(raw)} 字节")
    
    # 查找文件信息
    file_info = None
    for f in parser.files:
        if f['archive_path'] == item_path:
            file_info = f
            break
    
    if file_info:
        print(f"  data_type: {file_info['data_type']}")
        print(f"  size: {file_info['size']}")
    
    print()
    
    # 输出前200字节的hex
    print("  前200字节 hex:")
    for i in range(0, min(200, len(raw)), 16):
        hex_part = ' '.join(f'{b:02x}' for b in raw[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in raw[i:i+16])
        print(f"    {i:04x}: {hex_part:<48s} {ascii_part}")
    
    print()
    
    # 尝试直接UTF-8解码
    print("  尝试直接UTF-8解码（前500字符）:")
    try:
        text = raw.decode('utf-8', errors='replace')
        print(text[:500])
    except Exception as e:
        print(f"  解码失败: {e}")
    
    print()
    
    # 尝试GBK解码
    print("  尝试GBK解码（前500字符）:")
    try:
        text = raw.decode('gbk', errors='replace')
        print(text[:500])
    except Exception as e:
        print(f"  解码失败: {e}")
    
    print()
    
    # 使用解析器的read_file_text
    print("  使用解析器read_file_text:")
    text = parser.read_file_text(item_path)
    if text:
        print(text[:500])
    else:
        print("  空")
    
    return raw

def analyze_string_pool_encoding(parser):
    """分析字符串池的编码"""
    print(f"\n{'='*70}")
    print("字符串池编码分析")
    print(f"{'='*70}\n")
    
    if not parser.str_a:
        print("  字符串池为空")
        return
    
    print(f"  strA大小: {len(parser.str_a)} 字节")
    print()
    
    # 输出前100字节
    print("  前100字节 hex:")
    for i in range(0, min(100, len(parser.str_a)), 16):
        hex_part = ' '.join(f'{b:02x}' for b in parser.str_a[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in parser.str_a[i:i+16])
        print(f"    {i:04x}: {hex_part:<48s} {ascii_part}")
    
    print()
    
    # 搜索特定模式：UTF-8中文字符以0xE4-0xE9开头
    print("  搜索UTF-8中文字符模式（0xE4-0xE9开头）...")
    chinese_count = 0
    positions = []
    for i in range(len(parser.str_a)):
        if 0xE4 <= parser.str_a[i] <= 0xE9:
            # 检查是否是有效的UTF-8中文字符（3字节）
            if i + 2 < len(parser.str_a):
                b2 = parser.str_a[i+1]
                b3 = parser.str_a[i+2]
                if 0x80 <= b2 <= 0xBF and 0x80 <= b3 <= 0xBF:
                    chinese_count += 1
                    if len(positions) < 10:
                        positions.append(i)
    
    print(f"  找到 {chinese_count} 个可能的UTF-8中文字符")
    for pos in positions:
        # 读取到null
        end = parser.str_a.find(b'\x00', pos)
        if end < 0:
            end = min(pos + 100, len(parser.str_a))
        raw_str = parser.str_a[pos:end]
        try:
            text = raw_str.decode('utf-8', errors='replace')
            print(f"    偏移={pos}: {text[:50]}")
        except:
            pass
    
    print()
    
    # 搜索GBK中文字符模式（0x81-0xFE开头，第二字节0x40-0xFE）
    print("  搜索GBK中文字符模式...")
    gbk_count = 0
    gbk_positions = []
    for i in range(len(parser.str_a) - 1):
        b1 = parser.str_a[i]
        b2 = parser.str_a[i+1]
        if 0x81 <= b1 <= 0xFE and 0x40 <= b2 <= 0xFE and b2 != 0x7F:
            gbk_count += 1
            if len(gbk_positions) < 10:
                gbk_positions.append(i)
    
    print(f"  找到 {gbk_count} 个可能的GBK中文字符")
    for pos in gbk_positions:
        # 读取到null
        end = parser.str_a.find(b'\x00', pos)
        if end < 0:
            end = min(pos + 100, len(parser.str_a))
        raw_str = parser.str_a[pos:end]
        try:
            text = raw_str.decode('gbk', errors='replace')
            print(f"    偏移={pos}: {text[:50]}")
        except:
            pass

def test_decode_script(parser, item_path):
    """测试不同的脚本解码方式"""
    print(f"\n{'='*70}")
    print(f"测试脚本解码: {item_path}")
    print(f"{'='*70}\n")
    
    raw = parser.read_file_raw(item_path)
    if not raw:
        print("  未找到文件")
        return
    
    # 方式1：原始5字节token解码（当前方式）
    print("  [方式1] 5字节token解码（当前方式）:")
    result = []
    line_count = len(raw) // 5
    for idx in range(min(line_count, 100)):
        off = idx * 5
        token_type = raw[off]
        value = struct.unpack('<i', raw[off+1:off+5])[0]
        if token_type == 0:
            result.append(f"{value} ")
        elif token_type == 2:
            fval = struct.unpack('<f', struct.pack('<i', value))[0]
            result.append(f"{fval:.2f} ")
        elif token_type == 3:
            result.append('\n')
            result.append(parser._resolve_string(value))
            result.append('\n')
        elif token_type == 5:
            result.append('\n{5=``}')
        elif token_type == 6:
            result.append(f'`{parser._resolve_string(value)}` ')
        elif token_type == 7:
            result.append('\n{7=``}')
        else:
            result.append(f'[?{token_type}={value}]')
    print(''.join(result)[:500])
    
    print()
    
    # 方式2：检查前几个字节的token类型分布
    print("  [方式2] 前20个token类型分布:")
    for idx in range(min(20, line_count)):
        off = idx * 5
        token_type = raw[off]
        value = struct.unpack('<i', raw[off+1:off+5])[0]
        type_names = {0: '数字', 2: '浮点', 3: '换行+字符串', 5: '{5}', 6: '`字符串`', 7: '{7}'}
        tname = type_names.get(token_type, f'未知{token_type}')
        print(f"    [{idx:2d}] type={token_type} ({tname}), value={value} (0x{value:08x})")

def main():
    pvf_path = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf"
    
    # 解析PVF
    print("解析PVF文件...")
    parser = PVFParser(pvf_path)
    parser.load()
    print(f"  文件数: {parser.file_count}")
    
    # 1. 分析用户之前提供的物品（有中文名称的）
    item1 = "stackable/cash/chn_20140729_randombox/chn_clone_rare_avatarbox_2683816.stk"
    analyze_item_raw(parser, item1)
    
    # 2. 分析引用格式的物品
    item2 = "stackable/10000001/10000059.stk"
    analyze_item_raw(parser, item2)
    
    # 3. 分析字符串池编码
    analyze_string_pool_encoding(parser)
    
    # 4. 测试脚本解码
    test_decode_script(parser, item1)
    
    print(f"\n{'='*70}")
    print("分析完成！")
    print(f"{'='*70}\n")

if __name__ == '__main__':
    main()
