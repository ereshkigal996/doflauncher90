# -*- coding: utf-8 -*-
"""
分析.stk文件格式（TLV格式），找出物品名称的存储位置
"""
import sys
sys.path.insert(0, r'C:\Users\56518\Downloads\DBObject\pip\gmtool')

from pvf_parser import PVFParser

# 加载PVF
pvf_path = r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf'
parser = PVFParser(pvf_path)
parser.load()

print("=" * 60)
print("分析.stk文件格式（TLV格式）")
print("=" * 60)

# 找几个典型的.stk文件
test_files = [
    "stackable/10000001/10000039.stk",  # 普通消耗品
    "stackable/10094001/10094886.stk",  # 特殊物品
]

def parse_stk_tlv(raw, parser):
    """解析.stk文件的TLV格式"""
    result = []
    i = 0
    while i < len(raw):
        type_byte = raw[i]
        i += 1
        
        if type_byte == 0x01:  # 字节
            if i < len(raw):
                val = raw[i]
                result.append(('byte', i-1, val))
                i += 1
        elif type_byte == 0x02:  # 短整数
            if i + 2 <= len(raw):
                val = int.from_bytes(raw[i:i+2], 'little')
                result.append(('short', i-1, val))
                i += 2
        elif type_byte == 0x03:  # 整数
            if i + 4 <= len(raw):
                val = int.from_bytes(raw[i:i+4], 'little')
                result.append(('int', i-1, val))
                i += 4
        elif type_byte == 0x04:  # 长整数
            if i + 8 <= len(raw):
                val = int.from_bytes(raw[i:i+8], 'little')
                result.append(('long', i-1, val))
                i += 8
        elif type_byte == 0x05:  # 浮点数
            if i + 4 <= len(raw):
                import struct
                val = struct.unpack('<f', raw[i:i+4])[0]
                result.append(('float', i-1, val))
                i += 4
        elif type_byte == 0x06:  # 字符串索引
            if i + 4 <= len(raw):
                str_idx = int.from_bytes(raw[i:i+4], 'little')
                # 尝试解析字符串
                s = parser._resolve_string(str_idx)
                result.append(('string_idx', i-1, str_idx, s))
                i += 4
        elif type_byte == 0x07:  # 布尔
            if i < len(raw):
                val = raw[i] != 0
                result.append(('bool', i-1, val))
                i += 1
        elif type_byte == 0x00:  # 空/结束
            result.append(('null', i-1, None))
            break
        else:
            result.append(('unknown', i-1, type_byte))
            # 未知类型，尝试继续解析
            if i + 4 <= len(raw):
                val = int.from_bytes(raw[i:i+4], 'little')
                result.append(('  ?int', i, val))
                i += 4
    
    return result

for file_path in test_files:
    print(f"\n{'='*60}")
    print(f"文件: {file_path}")
    print('='*60)
    raw = parser.read_file_raw(file_path)
    if raw:
        print(f"文件大小: {len(raw)} 字节")
        print(f"\n前64字节十六进制:")
        for i in range(0, min(64, len(raw)), 16):
            hex_part = ' '.join(f'{b:02x}' for b in raw[i:i+16])
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in raw[i:i+16])
            print(f"  {i:04x}: {hex_part:<48s} {ascii_part}")
        
        print(f"\nTLV解析结果:")
        fields = parse_stk_tlv(raw, parser)
        for field in fields:
            if field[0] == 'string_idx':
                print(f"  偏移{field[1]:3d}: [字符串索引] 值={field[2]:6d} -> '{field[3]}'")
            elif field[0] in ('int', 'short', 'byte', 'long', 'float', 'bool'):
                print(f"  偏移{field[1]:3d}: [{field[0]}] 值={field[2]}")
            elif field[0] == 'null':
                print(f"  偏移{field[1]:3d}: [结束]")
                break
            else:
                print(f"  偏移{field[1]:3d}: [{field[0]}] 值={field[2]}")
    else:
        print("文件读取失败")

print("\n" + "=" * 60)
print("分析完成")
print("=" * 60)
