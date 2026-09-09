# -*- coding: utf-8 -*-
"""
分析.stk文件格式，找出物品名称的存储位置
"""
import sys
sys.path.insert(0, r'C:\Users\56518\Downloads\DBObject\pip\gmtool')

from pvf_parser import PVFParser

# 加载PVF
pvf_path = r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf'
parser = PVFParser(pvf_path)
parser.load()

print("=" * 60)
print("分析.stk文件格式")
print("=" * 60)

# 找几个典型的.stk文件
test_files = [
    "stackable/10000001/10000039.stk",  # 普通消耗品
    "stackable/10094001/10094886.stk",  # 特殊物品
    "stackable/cash/chn_490701780.stk",  # 商城物品
]

for file_path in test_files:
    print(f"\n--- 文件: {file_path} ---")
    raw = parser.read_file_raw(file_path)
    if raw:
        print(f"文件大小: {len(raw)} 字节")
        print(f"前128字节十六进制:")
        for i in range(0, min(128, len(raw)), 16):
            hex_part = ' '.join(f'{b:02x}' for b in raw[i:i+16])
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in raw[i:i+16])
            print(f"  {i:04x}: {hex_part:<48s} {ascii_part}")
        
        # 尝试解析前几个整数
        print(f"\n前20个小端整数:")
        for i in range(0, min(80, len(raw)), 4):
            if i + 4 <= len(raw):
                val = int.from_bytes(raw[i:i+4], 'little')
                signed = int.from_bytes(raw[i:i+4], 'little', signed=True)
                print(f"  偏移{i:3d}: {val:12d} (0x{val:08x}) 有符号: {signed}")
        
        # 尝试查找字符串表索引（通常是较小的数字）
        print(f"\n可能的字符串表索引（值<100000）:")
        for i in range(0, min(200, len(raw)), 4):
            if i + 4 <= len(raw):
                val = int.from_bytes(raw[i:i+4], 'little')
                if 0 < val < 100000:
                    # 尝试解析为字符串
                    s = parser.resolve_string(val)
                    if s and len(s) > 1:
                        print(f"  偏移{i:3d}: 值={val:6d} -> 字符串: '{s}'")
    else:
        print("文件读取失败")

print("\n" + "=" * 60)
print("分析完成")
print("=" * 60)
