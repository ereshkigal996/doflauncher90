# -*- coding: utf-8 -*-
"""
深入分析str_w解密失败的原因
"""
import sys
import os
import struct
import zlib

sys.path.insert(0, r"C:\Users\56518\Downloads\DBObject\pip\gmtool")
from pvf_parser import PVFParser

def analyze_str_w_decryption(parser):
    """分析str_w的解密过程"""
    print("=" * 70)
    print("str_w解密过程深度分析")
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
    print()
    
    # 分析str_a的位置和大小
    print("  [str_a 信息]")
    idx = 8
    encoded_size_a = struct.unpack('<I', name_bytes[idx:idx+4])[0]
    encoded_original_size_a = struct.unpack('<I', name_bytes[idx+4:idx+8])[0]
    enc_size_a = encoded_size_a ^ 0xAA74472E
    str_a_end = idx + 8 + enc_size_a
    
    print(f"    encoded_size: {encoded_size_a} (0x{encoded_size_a:x})")
    print(f"    enc_size (after xor): {enc_size_a}")
    print(f"    str_a结束位置: {str_a_end}")
    print(f"    str_a实际大小: {len(parser.str_a)}")
    print()
    
    # 分析str_w的原始数据
    print("  [str_w 原始数据分析]")
    idx_w = str_a_end
    print(f"    str_w起始位置: {idx_w}")
    
    if idx_w + 16 <= len(name_bytes):
        encoded_size_w = struct.unpack('<I', name_bytes[idx_w:idx_w+4])[0]
        encoded_original_size_w = struct.unpack('<I', name_bytes[idx_w+4:idx_w+8])[0]
        enc_size_w = encoded_size_w ^ 0x9A82F037
        
        print(f"    encoded_size: {encoded_size_w} (0x{encoded_size_w:x})")
        print(f"    encoded_original_size: {encoded_original_size_w}")
        print(f"    enc_size (after xor 0x9A82F037): {enc_size_w}")
        print()
        
        # 检查enc_size是否合理
        if enc_size_w <= 0 or idx_w + 8 + enc_size_w > len(name_bytes):
            print(f"    ⚠️ enc_size不合理！")
            print(f"       需要: {idx_w + 8 + enc_size_w}")
            print(f"       可用: {len(name_bytes)}")
            print()
        
        # 输出str_w原始数据的前100字节
        print("    str_w原始数据前100字节 hex:")
        raw_w = name_bytes[idx_w:idx_w + min(100, len(name_bytes) - idx_w)]
        for i in range(0, len(raw_w), 16):
            hex_part = ' '.join(f'{b:02x}' for b in raw_w[i:i+16])
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in raw_w[i:i+16])
            print(f"      {i:04x}: {hex_part:<48s} {ascii_part}")
        print()
        
        # 尝试不同的xor_const
        print("    [尝试不同的xor_const]")
        xor_candidates = [
            ("0x9A82F037 (当前)", 0x9A82F037),
            ("0x9A82F037 字节反转", 0x37F0829A),
            ("0xAA74472E (str_a的)", 0xAA74472E),
            ("0x269EC3", 0x269EC3),
            ("0x269EC9", 0x269EC9),
        ]
        
        for name, xor_const in xor_candidates:
            test_size = encoded_size_w ^ xor_const
            if 0 < test_size < 10000000 and idx_w + 8 + test_size <= len(name_bytes):
                print(f"      {name}: enc_size={test_size} ✓ (合理)")
            else:
                print(f"      {name}: enc_size={test_size} ✗ (不合理)")
        
        print()
        
        # 尝试手动解密str_w
        print("    [手动解密str_w测试]")
        
        # 使用当前方式解密
        encrypted = bytearray(name_bytes[idx_w+8:idx_w+8+enc_size_w])
        
        # 复制_decrypt_protected的逻辑
        key = "StRw"
        words = [ord(ch) for ch in key]
        magic = 0x269EC9  # 字符串池使用0x269EC9
        
        seed = (0x339E9711 * words[0] + 
                0x393 * (words[3] + 0x393 * (words[2] + 0x393 * words[1]))) & 0xFFFFFFFF
        
        size = len(encrypted)
        if size >= 4:
            quad_count = size >> 2
            for idx2 in range(quad_count):
                t1 = (0x343FD * seed + magic) & 0xFFFFFFFF
                seed = (0x343FD * t1 + magic) & 0xFFFFFFFF
                xor_key = ((t1 & 0xFFFF0000) + (seed >> 16)) & 0xFFFFFFFF
                off = idx2 << 2
                value = struct.unpack('<I', encrypted[off:off+4])[0] ^ xor_key
                struct.pack_into('<I', encrypted, off, value)
        
        # 尝试解压
        try:
            decompressed = zlib.decompress(bytes(encrypted))
            print(f"      解密+解压成功！大小: {len(decompressed)} 字节")
            
            # 检查是否有中文
            chinese_count = 0
            for i in range(len(decompressed) - 2):
                if 0xE4 <= decompressed[i] <= 0xE9 and 0x80 <= decompressed[i+1] <= 0xBF:
                    chinese_count += 1
            print(f"      UTF-8中文字符数: {chinese_count}")
            
            # 输出前200字节
            print(f"      前200字节:")
            preview = decompressed[:200]
            try:
                text = preview.decode('utf-8', errors='replace')
                print(f"        {text[:100]}")
            except:
                print(f"        hex: {preview[:50].hex()}")
                
        except Exception as e:
            print(f"      解密+解压失败: {e}")
            
            # 检查解密后的数据是否是zlib格式
            print(f"      解密后前4字节: {encrypted[:4].hex()}")
            print(f"      zlib魔数应该是: 78 9c 或 78 01 或 78 da")
        
        print()
        
        # 尝试不同的magic值
        print("    [尝试不同的magic值]")
        magic_candidates = [0x269EC3, 0x269EC9, 0x269EC0, 0x269EC5]
        for magic_test in magic_candidates:
            encrypted2 = bytearray(name_bytes[idx_w+8:idx_w+8+enc_size_w])
            seed2 = (0x339E9711 * words[0] + 
                    0x393 * (words[3] + 0x393 * (words[2] + 0x393 * words[1]))) & 0xFFFFFFFF
            size2 = len(encrypted2)
            if size2 >= 4:
                quad_count2 = size2 >> 2
                for idx2 in range(quad_count2):
                    t1 = (0x343FD * seed2 + magic_test) & 0xFFFFFFFF
                    seed2 = (0x343FD * t1 + magic_test) & 0xFFFFFFFF
                    xor_key = ((t1 & 0xFFFF0000) + (seed2 >> 16)) & 0xFFFFFFFF
                    off = idx2 << 2
                    value = struct.unpack('<I', encrypted2[off:off+4])[0] ^ xor_key
                    struct.pack_into('<I', encrypted2, off, value)
            
            try:
                zlib.decompress(bytes(encrypted2))
                print(f"      magic=0x{magic_test:x}: 成功 ✓")
            except:
                print(f"      magic=0x{magic_test:x}: 失败 ✗ (前4字节: {encrypted2[:4].hex()})")

def main():
    pvf_path = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf"
    
    print("解析PVF文件...")
    parser = PVFParser(pvf_path)
    parser.load()
    print(f"  strA大小: {len(parser.str_a) if parser.str_a else 0}")
    print(f"  strW大小: {len(parser.str_w) if parser.str_w else 0}")
    print()
    
    # 分析str_w解密
    analyze_str_w_decryption(parser)
    
    print()
    print("=" * 70)
    print("分析完成！")
    print("=" * 70)

if __name__ == '__main__':
    main()
