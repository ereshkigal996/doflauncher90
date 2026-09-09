# -*- coding: utf-8 -*-
"""
验证_resolve_string方法的问题，尝试直接读取偏移量
"""
import sys
import os
import struct

sys.path.insert(0, r"C:\Users\56518\Downloads\DBObject\pip\gmtool")
from pvf_parser import PVFParser

def read_string_at_offset(str_a, offset):
    """从字符串池指定偏移量读取字符串"""
    if not str_a or offset < 0 or offset >= len(str_a):
        return None, "偏移量超出范围"
    
    # 查找null结束
    end = str_a.find(b'\x00', offset)
    if end < 0:
        end = min(offset + 200, len(str_a))
    
    raw = str_a[offset:end]
    
    # 尝试UTF-8
    try:
        text = raw.decode('utf-8')
        return text, "UTF-8"
    except:
        pass
    
    # 尝试GBK
    try:
        text = raw.decode('gbk')
        return text, "GBK"
    except:
        pass
    
    # 尝试GB18030
    try:
        text = raw.decode('gb18030')
        return text, "GB18030"
    except:
        pass
    
    return raw.hex(), "raw hex"

def test_item_resolution(parser, item_path):
    """测试物品文件的字符串解析"""
    print(f"\n{'='*70}")
    print(f"测试物品: {item_path}")
    print(f"{'='*70}\n")
    
    raw = parser.read_file_raw(item_path)
    if not raw:
        print("  未找到文件")
        return
    
    # 解析前30个token
    print("  前30个token解析:\n")
    print(f"  {'序号':>4s}  {'类型':>4s}  {'类型名':<12s}  {'value(十进制)':>14s}  {'value(hex)':>12s}  {'最低位':>4s}  {'解析结果'}")
    print("  " + "-" * 120)
    
    line_count = len(raw) // 5
    for idx in range(min(line_count, 30)):
        off = idx * 5
        token_type = raw[off]
        value = struct.unpack('<i', raw[off+1:off+5])[0]
        
        type_names = {0: '数字', 2: '浮点', 3: '换行+字符串', 5: '{5}', 6: '`字符串`', 7: '{7}'}
        tname = type_names.get(token_type, f'未知{token_type}')
        
        if token_type in (3, 6) and value > 0:
            # 方式1：当前方式（判断最低位）
            if value & 1:
                resolved1 = "(UTF-16, 空)"
            else:
                resolved1 = parser._resolve_string(value)
                if not resolved1:
                    resolved1 = "(空)"
            
            # 方式2：直接当作UTF-8偏移量（不右移）
            text2, enc2 = read_string_at_offset(parser.str_a, value)
            
            # 方式3：右移1位当作UTF-8偏移量
            text3, enc3 = read_string_at_offset(parser.str_a, value >> 1)
            
            resolved = f"当前:{resolved1[:20]} | 直接:{text2[:20]}({enc2}) | 右移:{text3[:20]}({enc3})"
        else:
            resolved = str(value)
        
        lsb = value & 1
        print(f"  {idx:4d}  {token_type:4d}  {tname:<12s}  {value:14d}  0x{value:010x}  {lsb:4d}  {resolved[:80]}")

def search_chinese_in_pool(parser):
    """在字符串池中搜索中文内容"""
    print(f"\n{'='*70}")
    print("字符串池中文内容搜索")
    print(f"{'='*70}\n")
    
    if not parser.str_a:
        print("  字符串池为空")
        return
    
    # 搜索一些已知的中文词汇
    keywords = ['礼盒', '装备', '武器', '防具', '首饰', '消耗品', '材料', '任务', '称号', '宠物', '时装', '装扮']
    
    print("  搜索已知中文关键词...")
    for kw in keywords:
        kw_bytes = kw.encode('utf-8')
        idx = parser.str_a.find(kw_bytes)
        if idx >= 0:
            # 读取周围内容
            start = max(0, idx - 20)
            end = min(len(parser.str_a), idx + 100)
            raw = parser.str_a[start:end]
            try:
                text = raw.decode('utf-8', errors='replace')
                print(f"    找到 '{kw}'  at 偏移 {idx}:")
                print(f"      上下文: ...{text}...")
            except:
                pass
        else:
            # 尝试GBK
            kw_bytes_gbk = kw.encode('gbk')
            idx = parser.str_a.find(kw_bytes_gbk)
            if idx >= 0:
                print(f"    找到 '{kw}' (GBK) at 偏移 {idx}")
            else:
                print(f"    未找到 '{kw}'")

def main():
    pvf_path = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf"
    
    print("解析PVF文件...")
    parser = PVFParser(pvf_path)
    parser.load()
    print(f"  文件数: {parser.file_count}")
    print(f"  strA大小: {len(parser.str_a)} 字节")
    print(f"  strW大小: {len(parser.str_w) if parser.str_w else 0} 字节")
    
    # 1. 测试用户之前提供的物品
    item1 = "stackable/cash/chn_20140729_randombox/chn_clone_rare_avatarbox_2683816.stk"
    test_item_resolution(parser, item1)
    
    # 2. 测试引用格式的物品
    item2 = "stackable/10000001/10000059.stk"
    test_item_resolution(parser, item2)
    
    # 3. 搜索中文内容
    search_chinese_in_pool(parser)
    
    print(f"\n{'='*70}")
    print("测试完成！")
    print(f"{'='*70}\n")

if __name__ == '__main__':
    main()
