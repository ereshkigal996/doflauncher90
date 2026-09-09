# -*- coding: utf-8 -*-
"""详细分析原版GM工具的字符串，查找黑钻相关功能"""
import re

exe_path = r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\bin\DNF90GMTool.exe'

try:
    with open(exe_path, 'rb') as f:
        data = f.read()
    
    print(f"文件大小: {len(data)} 字节")
    print()
    
    # 提取UTF-8字符串（中文）
    print("=== 提取中文字符串 ===")
    # 匹配UTF-8编码的中文字符
    utf8_pattern = re.compile(b'[\xe4-\xe9][\x80-\xbf][\x80-\xbf](?:[\xe4-\xe9][\x80-\xbf][\x80-\xbf]|[\x20-\x7e])*')
    utf8_strings = utf8_pattern.findall(data)
    
    # 去重并排序
    unique_utf8 = list(set(utf8_strings))
    unique_utf8.sort()
    
    print(f"找到 {len(unique_utf8)} 个唯一中文字符串")
    print()
    
    # 查找与黑钻相关的中文字符串
    print("=== 与黑钻/会员/VIP相关的中文字符串 ===")
    keywords = ['黑钻', '黑砖', '会员', 'VIP', 'vip', '钻石', '特权', '服务', '期限', '到期', '开通', '续费', '等级']
    for s in unique_utf8:
        try:
            decoded = s.decode('utf-8', errors='replace')
            for kw in keywords:
                if kw in decoded:
                    print(f"  {decoded}")
                    break
        except:
            pass
    print()
    
    # 查找所有中文字符串（前100个）
    print("=== 所有中文字符串（前100个）===")
    for i, s in enumerate(unique_utf8[:100]):
        try:
            decoded = s.decode('utf-8', errors='replace')
            if len(decoded) > 2 and len(decoded) < 50:
                print(f"  {i+1}. {decoded}")
        except:
            pass
    print()
    
    # 提取ASCII字符串，查找与黑钻相关的
    print("=== 与black/dragon/vip/member/premium相关的ASCII字符串 ===")
    ascii_strings = re.findall(b'[\x20-\x7e]{4,}', data)
    unique_ascii = list(set(ascii_strings))
    unique_ascii.sort()
    
    ascii_keywords = [b'black', b'dragon', b'vip', b'member', b'premium', b'service', b'grade', b'rank', b'expire', b'cera', b'coin', b'gold']
    for s in unique_ascii:
        s_lower = s.lower()
        for kw in ascii_keywords:
            if kw in s_lower:
                try:
                    decoded = s.decode('ascii', errors='replace')
                    if len(decoded) > 3 and len(decoded) < 100:
                        print(f"  {decoded}")
                    break
                except:
                    pass
    print()
    
    # 查找SQL语句
    print("=== SQL语句相关字符串 ===")
    sql_keywords = [b'SELECT', b'UPDATE', b'INSERT', b'DELETE', b'FROM', b'WHERE', b'account', b'character', b'premium', b'black']
    for s in unique_ascii:
        s_upper = s.upper()
        if any(kw in s_upper for kw in sql_keywords):
            try:
                decoded = s.decode('ascii', errors='replace')
                if len(decoded) > 10 and len(decoded) < 200:
                    print(f"  {decoded}")
            except:
                pass
    print()
    
    print("分析完成！")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
