# -*- coding: utf-8 -*-
"""分析原版GM工具的二进制文件，查找与黑钻相关的字符串"""
import re
import os

# 原版GM工具路径
GM_TOOL_PATH = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\bin\DNF90GMTool.exe"

def extract_strings(file_path, min_length=4):
    """从二进制文件中提取字符串"""
    strings = []
    with open(file_path, 'rb') as f:
        data = f.read()
    
    # 提取ASCII字符串
    ascii_pattern = rb'[\x20-\x7e]{' + str(min_length).encode() + rb',}'
    ascii_matches = re.findall(ascii_pattern, data)
    for match in ascii_matches:
        try:
            s = match.decode('ascii', errors='replace')
            strings.append(s)
        except:
            pass
    
    # 提取UTF-16字符串（Windows常见）
    utf16_pattern = rb'(?:[\x20-\x7e]\x00){' + str(min_length).encode() + rb',}'
    utf16_matches = re.findall(utf16_pattern, data)
    for match in utf16_matches:
        try:
            s = match.decode('utf-16-le', errors='replace')
            strings.append(s)
        except:
            pass
    
    return strings

def main():
    print("=== 分析原版GM工具的二进制文件 ===")
    print()
    
    if not os.path.exists(GM_TOOL_PATH):
        print(f"错误: 文件不存在: {GM_TOOL_PATH}")
        return
    
    file_size = os.path.getsize(GM_TOOL_PATH)
    print(f"文件路径: {GM_TOOL_PATH}")
    print(f"文件大小: {file_size / 1024 / 1024:.2f} MB")
    print()
    
    # 提取字符串
    print("正在提取字符串...")
    strings = extract_strings(GM_TOOL_PATH, min_length=6)
    print(f"共提取到 {len(strings)} 个字符串")
    print()
    
    # 查找与黑钻相关的字符串
    print("=== 与黑钻相关的字符串 ===")
    black_diamond_keywords = ['black', 'diamond', 'premium', 'vip', '580', '581', '582', '583', '584', '585', '586', '587']
    black_diamond_strings = []
    for s in strings:
        s_lower = s.lower()
        for keyword in black_diamond_keywords:
            if keyword in s_lower:
                black_diamond_strings.append(s)
                break
    
    # 去重并排序
    black_diamond_strings = sorted(list(set(black_diamond_strings)))
    print(f"找到 {len(black_diamond_strings)} 个相关字符串:")
    print()
    for s in black_diamond_strings[:100]:
        print(f"  {s}")
    
    if len(black_diamond_strings) > 100:
        print(f"  ... 还有 {len(black_diamond_strings) - 100} 个")
    
    print()
    
    # 查找与API相关的字符串
    print("=== 与API相关的字符串 ===")
    api_keywords = ['/api/', 'http', 'localhost', '127.0.0.1', 'character', 'account']
    api_strings = []
    for s in strings:
        s_lower = s.lower()
        for keyword in api_keywords:
            if keyword in s_lower:
                api_strings.append(s)
                break
    
    api_strings = sorted(list(set(api_strings)))
    print(f"找到 {len(api_strings)} 个相关字符串:")
    print()
    for s in api_strings[:100]:
        print(f"  {s}")
    
    if len(api_strings) > 100:
        print(f"  ... 还有 {len(api_strings) - 100} 个")
    
    print()
    
    # 查找与数据库相关的字符串
    print("=== 与数据库相关的字符串 ===")
    db_keywords = ['mysql', 'sqlite', 'database', 'db_', 'query', 'insert', 'update', 'delete', 'select']
    db_strings = []
    for s in strings:
        s_lower = s.lower()
        for keyword in db_keywords:
            if keyword in s_lower:
                db_strings.append(s)
                break
    
    db_strings = sorted(list(set(db_strings)))
    print(f"找到 {len(db_strings)} 个相关字符串:")
    print()
    for s in db_strings[:100]:
        print(f"  {s}")
    
    if len(db_strings) > 100:
        print(f"  ... 还有 {len(db_strings) - 100} 个")
    
    print()
    
    # 保存所有字符串到文件
    print("正在保存所有字符串到文件...")
    with open(r'C:\Users\56518\Downloads\doubao_work\pip\gmtool_strings.txt', 'w', encoding='utf-8') as f:
        for s in sorted(list(set(strings))):
            f.write(s + '\n')
    print("已保存到 gmtool_strings.txt")
    
    print()
    print("=== 分析完成 ===")

if __name__ == "__main__":
    main()
