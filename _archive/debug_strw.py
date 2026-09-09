# -*- coding: utf-8 -*-
"""
详细调试str_w解密过程
"""
import sys
import os
import struct
import zlib

sys.path.insert(0, r"C:\Users\56518\Downloads\DBObject\pip\gmtool")
from pvf_parser import PVFParser

def debug_strw(parser):
    """详细调试str_w解密"""
    print("=" * 70)
    print("str_w解密详细调试")
    print("=" * 70)
    print()
    
    HEADER_SIZE = 0x30
    FILE_ITEM_SIZE = 0x18
    
    # 计算name_offset
    pos = HEADER_SIZE
    table_size = parser.file_count * FILE_ITEM_SIZE
    pos += table_size
    pos += parser.hash_size
    name_offset = pos
    
    name_bytes = parser.data[name_offset:name_offset + parser.name_size]
    
    print(f"  name_offset: {name_offset}")
    print(f"  name_size: {parser.name_size}")
    print(f"  name_bytes长度: {len(name_bytes)}")
    print()
    
    # 计算str_a_end
    idx = 8
    encoded_size_a = struct.unpack('<I', name_bytes[idx:idx+4])[0]
    enc_size_a = encoded_size_a ^ 0xAA74472E
    str_a_end = idx + 8 + enc_size_a
    
    print(f"  [str_a]")
    print(f"    encoded_size_a: {encoded_size_a} (0x{encoded_size_a:x})")
    print(f"    enc_size_a: {enc_size_a}")
    print(f"    str_a_end: {str_a_end}")
    print()
    
    # 检查str_a_end是否合理
    if str_a_end >= len(name_bytes):
        print(f"  ⚠️ str_a_end超出name_bytes范围！")
        print(f"     str_a_end={str_a_end}, len(name_bytes)={len(name_bytes)}")
        return
    
    # 获取str_w_bytes
    str_w_bytes = name_bytes[str_a_end:]
    print(f"  [str_w]")
    print(f"    str_w_bytes长度: {len(str_w_bytes)}")
    print()
    
    # 检查str_w_bytes的前16字节
    print(f"    str_w_bytes前16字节 hex:")
    print(f"      {str_w_bytes[:16].hex()}")
    print()
    
    # 手动解析str_w头部
    idx_w = 8
    if idx_w + 8 > len(str_w_bytes):
        print(f"  ⚠️ str_w_bytes长度不够，无法读取头部")
        return
    
    encoded_size_w = struct.unpack('<I', str_w_bytes[idx_w:idx_w+4])[0]
    encoded_original_size_w = struct.unpack('<I', str_w_bytes[idx_w+4:idx_w+8])[0]
    enc_size_w = encoded_size_w ^ 0x9A82F037
    
    print(f"    encoded_size_w: {encoded_size_w} (0x{encoded_size_w:x})")
    print(f"    encoded_original_size_w: {encoded_original_size_w}")
    print(f"    enc_size_w (after xor): {enc_size_w}")
    print()
    
    # 检查enc_size是否合理
    if enc_size_w <= 0:
        print(f"  ⚠️ enc_size_w <= 0")
        return
    
    if idx_w + 8 + enc_size_w > len(str_w_bytes):
        print(f"  ⚠️ enc_size_w超出范围！")
        print(f"     需要: {idx_w + 8 + enc_size_w}")
        print(f"     可用: {len(str_w_bytes)}")
        return
    
    print(f"    enc_size_w合理，开始解密...")
    print()
    
    # 手动解密
    encrypted = bytearray(str_w_bytes[idx_w+8:idx_w+8+enc_size_w])
    
    # 复制_decrypt_protected的逻辑
    key = "StRw"
    words = [ord(ch) for ch in key]
    magic = 0x269EC9
    
    seed = (0x339E9711 * words[0] + 
            0x393 * (words[3] + 0x393 * (words[2] + 0x393 * words[1]))) & 0xFFFFFFFF
    
    size = len(encrypted)
    if size >= 4:
        quad_count = size >> 2
        for i in range(quad_count):
            t1 = (0x343FD * seed + magic) & 0xFFFFFFFF
            seed = (0x343FD * t1 + magic) & 0xFFFFFFFF
            xor_key = ((t1 & 0xFFFF0000) + (seed >> 16)) & 0xFFFFFFFF
            off = i << 2
            value = struct.unpack('<I', encrypted[off:off+4])[0] ^ xor_key
            struct.pack_into('<I', encrypted, off, value)
    
    print(f"    解密完成，前4字节: {encrypted[:4].hex()}")
    print(f"    zlib魔数应该是: 78 9c / 78 01 / 78 da")
    print()
    
    # 尝试解压
    try:
        decompressed = zlib.decompress(bytes(encrypted))
        print(f"    ✓ zlib解压成功！大小: {len(decompressed)} 字节")
        
        # 检查内容
        print(f"    前100字节 hex: {decompressed[:100].hex()}")
        print()
        
        # 尝试不同编码
        print("    尝试不同编码:")
        try:
            text_utf16 = decompressed[:200].decode('utf-16-le', errors='replace')
            print(f"      UTF-16-LE: {text_utf16[:80]}")
        except Exception as e:
            print(f"      UTF-16-LE失败: {e}")
        
        try:
            text_utf8 = decompressed[:200].decode('utf-8', errors='replace')
            print(f"      UTF-8: {text_utf8[:80]}")
        except Exception as e:
            print(f"      UTF-8失败: {e}")
        
    except Exception as e:
        print(f"    ✗ zlib解压失败: {e}")
        
        # 尝试不同的wbits
        for wbits in [-15, -14, -13, 15, 31]:
            try:
                d = zlib.decompress(bytes(encrypted), wbits)
                print(f"    wbits={wbits}: 成功，大小={len(d)}")
                break
            except:
                pass

def main():
    pvf_path = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf"
    
    print("解析PVF文件...")
    parser = PVFParser(pvf_path)
    parser.load()
    
    print()
    print(f"  strA大小: {len(parser.str_a) if parser.str_a else 0}")
    print(f"  strW大小: {len(parser.str_w) if parser.str_w else 0}")
    print()
    
    # 详细调试
    debug_strw(parser)
    
    print()
    print("调试完成！")

if __name__ == '__main__':
    main()
