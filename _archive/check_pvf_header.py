# -*- coding: utf-8 -*-
"""
检查PVF文件头的原始字节
"""
import struct

pvf_path = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf"

print("=" * 60)
print("PVF文件头原始字节检查")
print("=" * 60)
print(f"文件: {pvf_path}")
print()

with open(pvf_path, 'rb') as f:
    # 读取前100字节
    header_bytes = f.read(100)
    
    print("前100字节的十六进制表示:")
    for i in range(0, len(header_bytes), 16):
        hex_part = ' '.join(f'{b:02x}' for b in header_bytes[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in header_bytes[i:i+16])
        print(f"  {i:04x}: {hex_part:<48s} {ascii_part}")
    print()
    
    # 尝试解析
    print("尝试解析文件头:")
    f.seek(0)
    
    # 读取uuid_len
    uuid_len_bytes = f.read(4)
    uuid_len = struct.unpack('i', uuid_len_bytes)[0]
    print(f"  uuid_len (4字节int): {uuid_len}")
    
    # 读取uuid
    uuid_bytes = f.read(uuid_len)
    print(f"  uuid ({uuid_len}字节): {uuid_bytes[:50]}")
    try:
        uuid_str = uuid_bytes.decode('ascii', errors='replace')
        print(f"  uuid (ASCII): {uuid_str}")
    except:
        pass
    
    # 读取下一个4字节
    next_bytes = f.read(4)
    print(f"  下一个4字节: {next_bytes.hex()}")
    try:
        version = struct.unpack('i', next_bytes)[0]
        print(f"  作为int解析: {version}")
    except Exception as e:
        print(f"  解析失败: {e}")
    
    # 再读取一些
    more_bytes = f.read(20)
    print(f"  再读取20字节: {more_bytes.hex()}")
    
print()
print("=" * 60)
print("检查完成")
print("=" * 60)
