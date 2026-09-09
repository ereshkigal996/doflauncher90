# -*- coding: utf-8 -*-
"""深入分析原版GM工具的黑钻API实现"""
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
    
    return strings

def find_context(strings, keyword, context_size=5):
    """查找包含关键词的字符串及其上下文"""
    results = []
    for i, s in enumerate(strings):
        if keyword.lower() in s.lower():
            start = max(0, i - context_size)
            end = min(len(strings), i + context_size + 1)
            context = strings[start:end]
            results.append({
                'index': i,
                'match': s,
                'context': context
            })
    return results

def main():
    print("=== 深入分析原版GM工具的黑钻API实现 ===")
    print()
    
    if not os.path.exists(GM_TOOL_PATH):
        print(f"错误: 文件不存在: {GM_TOOL_PATH}")
        return
    
    # 提取字符串
    print("正在提取字符串...")
    strings = extract_strings(GM_TOOL_PATH, min_length=6)
    print(f"共提取到 {len(strings)} 个字符串")
    print()
    
    # 1. 查找与black-diamond API相关的字符串
    print("=== 1. 与black-diamond API相关的字符串 ===")
    api_results = find_context(strings, 'black-diamond', context_size=10)
    for result in api_results:
        print(f"位置: {result['index']}")
        print(f"匹配: {result['match']}")
        print("上下文:")
        for i, ctx in enumerate(result['context']):
            marker = " >>>" if i == (result['index'] - max(0, result['index'] - 10)) else "    "
            print(f"{marker} {ctx}")
        print()
    
    # 2. 查找与premium相关的字符串
    print("=== 2. 与premium相关的字符串 ===")
    premium_results = find_context(strings, 'premium', context_size=5)
    print(f"找到 {len(premium_results)} 个匹配")
    for result in premium_results[:20]:
        print(f"  {result['match']}")
    print()
    
    # 3. 查找与数据库操作相关的字符串
    print("=== 3. 与数据库操作相关的字符串 ===")
    db_keywords = ['INSERT INTO', 'UPDATE ', 'SELECT ', 'DELETE FROM', 'dnf_account', 'dnf_character']
    for keyword in db_keywords:
        db_results = find_context(strings, keyword, context_size=3)
        if db_results:
            print(f"关键词 '{keyword}': 找到 {len(db_results)} 个匹配")
            for result in db_results[:5]:
                print(f"  {result['match']}")
    print()
    
    # 4. 查找与服务端API调用相关的字符串
    print("=== 4. 与服务端API调用相关的字符串 ===")
    server_keywords = ['http://', 'https://', 'localhost:', '127.0.0.1:', '/api/', '/gateway/', '/logic/']
    for keyword in server_keywords:
        server_results = find_context(strings, keyword, context_size=3)
        if server_results:
            print(f"关键词 '{keyword}': 找到 {len(server_results)} 个匹配")
            for result in server_results[:10]:
                print(f"  {result['match']}")
    print()
    
    # 5. 查找与黑钻相关的所有字符串（更广泛的搜索）
    print("=== 5. 与黑钻相关的所有字符串 ===")
    black_diamond_keywords = ['black', 'diamond', '580', '581', '582', '583', '584', '585', '586', '587', 'expire']
    all_related = set()
    for s in strings:
        s_lower = s.lower()
        for keyword in black_diamond_keywords:
            if keyword in s_lower and len(s) < 200:
                all_related.add(s)
                break
    
    print(f"找到 {len(all_related)} 个相关字符串:")
    for s in sorted(all_related):
        print(f"  {s}")
    print()
    
    # 6. 查找Go语言的函数名（可能包含黑钻相关的处理函数）
    print("=== 6. 可能的Go函数名 ===")
    go_func_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*$')
    go_funcs = []
    for s in strings:
        if go_func_pattern.match(s) and len(s) < 100:
            # 过滤掉常见的非函数名字符串
            if any(keyword in s.lower() for keyword in ['black', 'diamond', 'premium', 'character', 'account', 'api', 'handler']):
                go_funcs.append(s)
    
    print(f"找到 {len(go_funcs)} 个可能的函数名:")
    for s in sorted(set(go_funcs)):
        print(f"  {s}")
    print()
    
    print("=== 分析完成 ===")

if __name__ == "__main__":
    main()
