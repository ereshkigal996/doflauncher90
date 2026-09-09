# -*- coding: utf-8 -*-
"""测试原版GM工具的HTTP API"""
import urllib.request
import urllib.error
import json

API_URL = "http://127.0.0.1:53322"

def call_api(path, method="GET", data=None):
    """调用API接口"""
    url = f"{API_URL}{path}"
    try:
        headers = {
            "Content-Type": "application/json",
        }
        
        if method == "GET":
            req = urllib.request.Request(url, headers=headers, method="GET")
        elif method == "POST":
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8') if data else None, headers=headers, method="POST")
        else:
            return None, "Unsupported method"
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, response.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None, str(e)

def main():
    print("=== 测试原版GM工具的HTTP API ===")
    print(f"API URL: {API_URL}")
    print()
    
    # 1. 测试根路径
    print("=== 1. 根路径 ===")
    status, text = call_api("/")
    print(f"状态码: {status}")
    print(f"响应: {text[:1000]}")
    print()
    
    # 2. 测试/api路径
    print("=== 2. /api路径 ===")
    status, text = call_api("/api")
    print(f"状态码: {status}")
    print(f"响应: {text[:500]}")
    print()
    
    # 3. 测试/api/settings
    print("=== 3. /api/settings ===")
    status, text = call_api("/api/settings")
    print(f"状态码: {status}")
    print(f"响应: {text[:500]}")
    print()
    
    # 4. 测试/api/character
    print("=== 4. /api/character ===")
    status, text = call_api("/api/character")
    print(f"状态码: {status}")
    print(f"响应: {text[:500]}")
    print()
    
    # 5. 测试/api/characters
    print("=== 5. /api/characters ===")
    status, text = call_api("/api/characters")
    print(f"状态码: {status}")
    print(f"响应: {text[:1000]}")
    print()
    
    # 6. 测试/api/wallet/query
    print("=== 6. /api/wallet/query ===")
    status, text = call_api("/api/wallet/query")
    print(f"状态码: {status}")
    print(f"响应: {text[:500]}")
    print()
    
    # 7. 测试/api/select-pvf
    print("=== 7. /api/select-pvf ===")
    status, text = call_api("/api/select-pvf", method="POST", data={})
    print(f"状态码: {status}")
    print(f"响应: {text[:500]}")
    print()
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    main()
