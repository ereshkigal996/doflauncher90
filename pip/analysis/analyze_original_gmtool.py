# -*- coding: utf-8 -*-
"""分析原版GM工具，查找黑钻相关功能"""
import re
import sys

exe_path = r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\bin\DNF90GMTool.exe'

try:
    with open(exe_path, 'rb') as f:
        data = f.read()
    
    # 提取可打印字符串（长度>=4）
    strings = re.findall(b'[\x20-\x7e]{4,}', data)
    
    # 查找关键词
    keywords = [b'black', b'dragon', b'vip', b'member', b'premium', b'cera', b'coin', b'token', b'expire', b'service', b'grade', b'rank']
    
    print(f'文件大小: {len(data)} 字节')
    print(f'提取到 {len(strings)} 个字符串')
    print()
    print('=== 包含关键词的字符串 ===')
    for s in strings:
        s_lower = s.lower()
        for kw in keywords:
            if kw in s_lower:
                try:
                    print(f'  {s.decode("ascii", errors="replace")}')
                except:
                    print(f'  {s}')
                break
    
    print()
    print('=== 查找SQL语句相关字符串 ===')
    sql_keywords = [b'SELECT', b'UPDATE', b'INSERT', b'DELETE', b'FROM', b'WHERE', b'account', b'character']
    for s in strings:
        s_upper = s.upper()
        if any(kw in s_upper for kw in sql_keywords):
            try:
                decoded = s.decode("ascii", errors="replace")
                if len(decoded) > 10 and len(decoded) < 200:
                    print(f'  {decoded}')
            except:
                pass
    
    print()
    print('=== 查找UI界面相关字符串 ===')
    ui_keywords = ['按钮', '菜单', '设置', '角色', '账号', '物品', '邮件', '点券', '金币', '黑钻', '会员', 'VIP']
    for s in strings:
        try:
            decoded = s.decode("utf-8", errors="replace")
            for kw in ui_keywords:
                if kw in decoded:
                    print(f'  {decoded}')
                    break
        except:
            pass
    
    print()
    print('分析完成！')
    
except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()
