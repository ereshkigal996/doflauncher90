# -*- coding: utf-8 -*-
"""
深入分析.equ和.stk文件格式，找出物品名称的存储位置
"""
import sys
sys.path.insert(0, r'C:\Users\56518\Downloads\DBObject\pip\gmtool')

from pvf_parser import PVFParser
import struct

# 加载PVF
pvf_path = r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf'
parser = PVFParser(pvf_path)
parser.load()

print("=" * 70)
print("深入分析.equ和.stk文件格式")
print("=" * 70)

def analyze_file(file_path, file_type):
    """分析单个文件"""
    print(f"\n{'='*70}")
    print(f"文件类型: {file_type}")
    print(f"文件路径: {file_path}")
    print('='*70)
    
    raw = parser.read_file_raw(file_path)
    if not raw:
        print("文件读取失败")
        return
    
    print(f"文件大小: {len(raw)} 字节")
    
    # 显示前256字节十六进制
    print(f"\n前256字节十六进制:")
    for i in range(0, min(256, len(raw)), 16):
        hex_part = ' '.join(f'{b:02x}' for b in raw[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in raw[i:i+16])
        print(f"  {i:04x}: {hex_part:<48s} {ascii_part}")
    
    # 尝试解析为TLV格式
    print(f"\n尝试TLV解析（前50个字段）:")
    i = 0
    field_count = 0
    while i < len(raw) and field_count < 50:
        if i >= len(raw):
            break
        type_byte = raw[i]
        i += 1
        
        if type_byte == 0x00:  # 空/结束
            print(f"  偏移{i-1:3d}: [0x00 结束]")
            break
        elif type_byte == 0x01:  # 字节
            if i < len(raw):
                print(f"  偏移{i-1:3d}: [byte] {raw[i]}")
                i += 1
        elif type_byte == 0x02:  # 短整数
            if i + 2 <= len(raw):
                val = struct.unpack('<H', raw[i:i+2])[0]
                print(f"  偏移{i-1:3d}: [short] {val}")
                i += 2
        elif type_byte == 0x03:  # 整数
            if i + 4 <= len(raw):
                val = struct.unpack('<I', raw[i:i+4])[0]
                signed = struct.unpack('<i', raw[i:i+4])[0]
                print(f"  偏移{i-1:3d}: [int] {val} (signed: {signed})")
                i += 4
        elif type_byte == 0x04:  # 长整数
            if i + 8 <= len(raw):
                val = struct.unpack('<Q', raw[i:i+8])[0]
                print(f"  偏移{i-1:3d}: [long] {val}")
                i += 8
        elif type_byte == 0x05:  # 浮点数
            if i + 4 <= len(raw):
                val = struct.unpack('<f', raw[i:i+4])[0]
                print(f"  偏移{i-1:3d}: [float] {val}")
                i += 4
        elif type_byte == 0x06:  # 字符串索引
            if i + 4 <= len(raw):
                str_idx = struct.unpack('<I', raw[i:i+4])[0]
                s = parser._resolve_string(str_idx)
                print(f"  偏移{i-1:3d}: [string_idx] {str_idx} -> '{s}'")
                i += 4
        elif type_byte == 0x07:  # 布尔
            if i < len(raw):
                print(f"  偏移{i-1:3d}: [bool] {raw[i] != 0}")
                i += 1
        elif type_byte == 0x08:  # 字符串（直接存储）
            if i + 2 <= len(raw):
                str_len = struct.unpack('<H', raw[i:i+2])[0]
                i += 2
                if i + str_len <= len(raw):
                    try:
                        s = raw[i:i+str_len].decode('utf-8', errors='replace')
                    except:
                        s = str(raw[i:i+str_len])
                    print(f"  偏移{i-3:3d}: [string len={str_len}] '{s}'")
                    i += str_len
        elif type_byte == 0x09:  # 数组
            if i + 4 <= len(raw):
                arr_len = struct.unpack('<I', raw[i:i+4])[0]
                print(f"  偏移{i-1:3d}: [array] 长度={arr_len}")
                i += 4
        else:
            print(f"  偏移{i-1:3d}: [unknown 0x{type_byte:02x}]")
            # 尝试继续
            if i + 4 <= len(raw):
                val = struct.unpack('<I', raw[i:i+4])[0]
                print(f"           后续4字节: {val}")
                i += 4
        
        field_count += 1
    
    # 尝试查找所有可能的字符串索引（值在合理范围内）
    print(f"\n扫描所有可能的字符串索引（值<500000且能解析出非空字符串）:")
    found_strings = []
    for i in range(0, min(len(raw)-4, 500), 1):
        if i + 4 <= len(raw):
            val = struct.unpack('<I', raw[i:i+4])[0]
            if 0 < val < 500000:
                s = parser._resolve_string(val)
                if s and len(s) >= 2 and any('\u4e00' <= c <= '\u9fff' for c in s):
                    found_strings.append((i, val, s))
    
    for offset, idx, s in found_strings[:20]:
        print(f"  偏移{offset:3d}: 索引={idx:6d} -> '{s}'")
    
    if len(found_strings) > 20:
        print(f"  ... 还有 {len(found_strings)-20} 个")

# 分析几个典型文件
test_files = [
    # 消耗品
    ("stackable/10000001/10000039.stk", "消耗品-低级HP药"),
    ("stackable/cash/chn_490701780.stk", "消耗品-商城物品"),
    # 装备
    ("equipment/character/common/amulet/100300001.equ", "装备-项链"),
    ("equipment/character/gunner/weapon/10000001.equ", "装备-武器(如果存在)"),
    # 时装
    ("character/gunner/avatar/coat/10000001.equ", "时装-上衣(如果存在)"),
]

for file_path, desc in test_files:
    # 检查文件是否存在
    found = False
    for f in parser.files:
        if f['archive_path'].lower() == file_path.lower():
            found = True
            break
    
    if found:
        analyze_file(file_path, desc)
    else:
        print(f"\n文件不存在: {file_path} ({desc})")
        # 查找类似文件
        print("查找类似文件...")
        similar = []
        for f in parser.files:
            if file_path.split('/')[-1].split('.')[0] in f['name']:
                similar.append(f['archive_path'])
                if len(similar) >= 5:
                    break
        for s in similar:
            print(f"  {s}")

print("\n" + "=" * 70)
print("分析完成")
print("=" * 70)
