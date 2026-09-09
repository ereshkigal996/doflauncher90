# -*- coding: utf-8 -*-
"""
深入分析PVF字符串池结构和奇数value引用问题
"""
import sys
import os
import struct
import zlib

sys.path.insert(0, r"C:\Users\56518\Downloads\DBObject\pip\gmtool")
from pvf_parser import PVFParser

def analyze_string_pool_structure(parser):
    """分析字符串池的原始结构"""
    print("=" * 70)
    print("字符串池原始结构分析")
    print("=" * 70)
    print()
    
    # 计算name_offset
    HEADER_SIZE = 0x30
    FILE_ITEM_SIZE = 0x18
    
    pos = HEADER_SIZE
    table_size = parser.file_count * FILE_ITEM_SIZE
    pos += table_size
    pos += parser.hash_size
    name_offset = pos
    
    print(f"  name_offset: {name_offset} (0x{name_offset:x})")
    print(f"  name_size: {parser.name_size} (0x{parser.name_size:x})")
    print()
    
    # 读取name_bytes的前200字节
    name_bytes = parser.data[name_offset:name_offset + min(200, parser.name_size)]
    
    print("  name_bytes 前200字节 hex:")
    for i in range(0, len(name_bytes), 16):
        hex_part = ' '.join(f'{b:02x}' for b in name_bytes[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in name_bytes[i:i+16])
        print(f"    {i:04x}: {hex_part:<48s} {ascii_part}")
    
    print()
    
    # 分析str_a的解析
    print("  [str_a 解析分析]")
    print(f"    密钥: StRa, xor_const: 0xAA74472E")
    
    # 手动解析str_a
    idx = 8
    encoded_size = struct.unpack('<I', parser.data[name_offset + idx:name_offset + idx + 4])[0]
    encoded_original_size = struct.unpack('<I', parser.data[name_offset + idx + 4:name_offset + idx + 8])[0]
    enc_size = encoded_size ^ 0xAA74472E
    
    print(f"    encoded_size: {encoded_size} (0x{encoded_size:x})")
    print(f"    encoded_original_size: {encoded_original_size}")
    print(f"    enc_size (after xor): {enc_size}")
    print(f"    str_a 实际大小: {len(parser.str_a) if parser.str_a else 0}")
    
    print()
    
    # 分析str_w的解析
    print("  [str_w 解析分析]")
    print(f"    密钥: StRw, xor_const: 0x9A82F037")
    
    # str_w应该在str_a之后
    str_a_end = 8 + 8 + enc_size  # idx(8) + header(8) + data
    print(f"    str_a结束位置: {str_a_end}")
    
    if str_a_end + 16 < parser.name_size:
        idx2 = str_a_end
        encoded_size_w = struct.unpack('<I', parser.data[name_offset + idx2:name_offset + idx2 + 4])[0]
        encoded_original_size_w = struct.unpack('<I', parser.data[name_offset + idx2 + 4:name_offset + idx2 + 8])[0]
        enc_size_w = encoded_size_w ^ 0x9A82F037
        
        print(f"    encoded_size: {encoded_size_w} (0x{encoded_size_w:x})")
        print(f"    encoded_original_size: {encoded_original_size_w}")
        print(f"    enc_size (after xor): {enc_size_w}")
        print(f"    str_w 实际大小: {len(parser.str_w) if parser.str_w else 0}")
        
        if enc_size_w > 0 and enc_size_w < 100000000:
            print(f"    str_w 应该有数据，但实际为空，可能解密失败！")
    else:
        print(f"    str_a结束位置已超出name_size，可能没有str_w")
    
    print()

def test_odd_value_resolution(parser, item_path):
    """测试奇数value的多种解析方式"""
    print("=" * 70)
    print(f"奇数value解析测试: {item_path}")
    print("=" * 70)
    print()
    
    raw = parser.read_file_raw(item_path)
    if not raw:
        print("  未找到文件")
        return
    
    # 找到[name]标签后的第一个type=6 token
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
            print(f"  [name]后的token: idx={idx}, value={value} (0x{value:x}), 最低位={value & 1}")
            print()
            
            # 方式1：当前方式（奇数→UTF-16）
            print("  [方式1] 当前方式（奇数→UTF-16）:")
            r1 = parser._resolve_string(value)
            print(f"    结果: '{r1}'")
            print()
            
            # 方式2：直接当作UTF-8偏移量（不右移）
            print("  [方式2] 直接当作UTF-8偏移量（不右移）:")
            if 0 <= value < len(parser.str_a):
                end = parser.str_a.find(b'\x00', value)
                if end < 0: end = min(value + 200, len(parser.str_a))
                try:
                    r2 = parser.str_a[value:end].decode('utf-8', errors='replace')
                    print(f"    结果: '{r2[:80]}'")
                except:
                    print(f"    解码失败")
            else:
                print(f"    偏移量超出范围 (max={len(parser.str_a)})")
            print()
            
            # 方式3：右移1位当作UTF-8偏移量
            print("  [方式3] 右移1位当作UTF-8偏移量:")
            offset3 = value >> 1
            if 0 <= offset3 < len(parser.str_a):
                end = parser.str_a.find(b'\x00', offset3)
                if end < 0: end = min(offset3 + 200, len(parser.str_a))
                try:
                    r3 = parser.str_a[offset3:end].decode('utf-8', errors='replace')
                    print(f"    偏移量: {offset3}")
                    print(f"    结果: '{r3[:80]}'")
                except:
                    print(f"    解码失败")
            else:
                print(f"    偏移量超出范围")
            print()
            
            # 方式4：清除最低位后右移
            print("  [方式4] 清除最低位后右移:")
            offset4 = (value & ~1) >> 1
            if 0 <= offset4 < len(parser.str_a):
                end = parser.str_a.find(b'\x00', offset4)
                if end < 0: end = min(offset4 + 200, len(parser.str_a))
                try:
                    r4 = parser.str_a[offset4:end].decode('utf-8', errors='replace')
                    print(f"    偏移量: {offset4}")
                    print(f"    结果: '{r4[:80]}'")
                except:
                    print(f"    解码失败")
            else:
                print(f"    偏移量超出范围")
            print()
            
            # 方式5：value作为索引，查找字符串池中的某个结构
            print("  [方式5] 检查value附近的字符串池内容:")
            for test_offset in [value, value >> 1, (value & ~1) >> 1]:
                if 0 <= test_offset < len(parser.str_a):
                    # 读取前后各50字节
                    start = max(0, test_offset - 20)
                    end = min(len(parser.str_a), test_offset + 100)
                    raw_data = parser.str_a[start:end]
                    try:
                        text = raw_data.decode('utf-8', errors='replace')
                        print(f"    偏移{test_offset}附近: ...{text[:80]}...")
                    except:
                        pass
            print()
            
            break

def search_chinese_in_raw_pool(parser):
    """在原始未解密的字符串池中搜索中文"""
    print("=" * 70)
    print("原始字符串池中文搜索")
    print("=" * 70)
    print()
    
    HEADER_SIZE = 0x30
    FILE_ITEM_SIZE = 0x18
    
    pos = HEADER_SIZE
    table_size = parser.file_count * FILE_ITEM_SIZE
    pos += table_size
    pos += parser.hash_size
    name_offset = pos
    
    raw_name = parser.data[name_offset:name_offset + parser.name_size]
    
    print(f"  原始name_bytes大小: {len(raw_name)}")
    print()
    
    # 搜索UTF-8中文
    print("  搜索UTF-8中文模式...")
    utf8_count = 0
    for i in range(len(raw_name) - 2):
        if 0xE4 <= raw_name[i] <= 0xE9 and 0x80 <= raw_name[i+1] <= 0xBF and 0x80 <= raw_name[i+2] <= 0xBF:
            utf8_count += 1
            if utf8_count <= 5:
                # 读取周围内容
                start = max(0, i - 10)
                end = min(len(raw_name), i + 50)
                raw_data = raw_name[start:end]
                try:
                    text = raw_data.decode('utf-8', errors='replace')
                    print(f"    偏移{i}: ...{text[:60]}...")
                except:
                    pass
    
    print(f"  找到 {utf8_count} 个UTF-8中文字符")
    print()
    
    # 搜索GBK中文
    print("  搜索GBK中文模式...")
    gbk_count = 0
    for i in range(len(raw_name) - 1):
        b1 = raw_name[i]
        b2 = raw_name[i+1]
        if 0x81 <= b1 <= 0xFE and 0x40 <= b2 <= 0xFE and b2 != 0x7F:
            gbk_count += 1
            if gbk_count <= 5:
                start = max(0, i - 10)
                end = min(len(raw_name), i + 50)
                raw_data = raw_name[start:end]
                try:
                    text = raw_data.decode('gbk', errors='replace')
                    print(f"    偏移{i}: ...{text[:60]}...")
                except:
                    pass
    
    print(f"  找到 {gbk_count} 个GBK中文字符")

def main():
    pvf_path = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf"
    
    print("解析PVF文件...")
    parser = PVFParser(pvf_path)
    parser.load()
    print(f"  文件数: {parser.file_count}")
    print(f"  strA大小: {len(parser.str_a) if parser.str_a else 0}")
    print(f"  strW大小: {len(parser.str_w) if parser.str_w else 0}")
    print()
    
    # 1. 分析字符串池结构
    analyze_string_pool_structure(parser)
    
    # 2. 测试奇数value解析
    item1 = "stackable/cash/chn_20140729_randombox/chn_clone_rare_avatarbox_2683816.stk"
    test_odd_value_resolution(parser, item1)
    
    # 3. 搜索原始字符串池中的中文
    search_chinese_in_raw_pool(parser)
    
    print()
    print("=" * 70)
    print("分析完成！")
    print("=" * 70)

if __name__ == '__main__':
    main()
