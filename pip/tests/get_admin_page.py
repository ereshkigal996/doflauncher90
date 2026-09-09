# -*- coding: utf-8 -*-
"""获取/admin页面的JavaScript部分"""
import urllib.request
import urllib.error
import re

API_URL = "http://127.0.0.1:18111"
ADMIN_TOKEN = "adm_1e3178c6770ceaaa2a63ed44e20a17e4"

def main():
    print("=== 获取/admin页面完整内容 ===")
    url = f"{API_URL}/admin"
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            text = response.read().decode('utf-8', errors='replace')
        
        print(f"内容长度: {len(text)}")
        print()
        
        # 查找<script>标签
        print("=== 查找<script>标签 ===")
        script_pattern = r'<script[^>]*>(.*?)</script>'
        scripts = re.findall(script_pattern, text, re.DOTALL)
        print(f"找到 {len(scripts)} 个script标签")
        print()
        
        for i, script in enumerate(scripts):
            print(f"=== Script {i+1} (长度: {len(script)}) ===")
            print(script[:3000])
            print()
        
        # 查找所有API路径（以/开头的路径）
        print("=== 查找所有API路径 ===")
        api_paths = re.findall(r'["\'](/[a-zA-Z0-9_/\-]+)["\']', text)
        unique_paths = list(set(api_paths))
        unique_paths.sort()
        for path in unique_paths:
            print(f"  {path}")
        print()
        
        # 查找fetch调用
        print("=== 查找fetch调用 ===")
        fetch_pattern = r'fetch\(([^)]+)\)'
        fetch_calls = re.findall(fetch_pattern, text)
        for i, call in enumerate(fetch_calls):
            print(f"  fetch调用 {i+1}: {call[:200]}")
        print()
        
        # 保存完整页面到文件
        with open(r'C:\Users\56518\Downloads\doubao_work\pip\admin_page.html', 'w', encoding='utf-8') as f:
            f.write(text)
        print("页面已保存到 admin_page.html")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
