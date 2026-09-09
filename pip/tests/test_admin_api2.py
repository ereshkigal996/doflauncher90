# -*- coding: utf-8 -*-
"""测试服务端管理API（使用urllib）"""
import urllib.request
import urllib.error
import json

API_URL = "http://127.0.0.1:18111"
ADMIN_TOKEN = "adm_1e3178c6770ceaaa2a63ed44e20a17e4"

def test_api(path, method="GET", data=None):
    """测试API接口"""
    url = f"{API_URL}{path}"
    try:
        headers = {
            "Authorization": f"Bearer {ADMIN_TOKEN}",
            "Content-Type": "application/json"
        }
        
        if method == "GET":
            req = urllib.request.Request(url, headers=headers, method="GET")
        elif method == "POST":
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8') if data else None, headers=headers, method="POST")
        else:
            return None, "Unsupported method"
        
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, response.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None, str(e)

def main():
    print("=== 测试服务端管理API ===")
    print(f"API URL: {API_URL}")
    print()
    
    # 测试常见的API路径
    test_paths = [
        "/",
        "/health",
        "/api",
        "/api/",
        "/admin",
        "/admin/",
        "/api/health",
        "/api/status",
        "/api/account",
        "/api/accounts",
        "/api/character",
        "/api/characters",
        "/api/premium",
        "/api/vip",
        "/api/member",
        "/api/black-dragon",
        "/api/blackdragon",
        "/api/service",
        "/api/services",
        "/api/cera",
        "/api/gold",
        "/api/item",
        "/api/items",
        "/api/mail",
        "/api/mails",
    ]
    
    print("=== 测试API路径 ===")
    found_apis = []
    for path in test_paths:
        status, text = test_api(path)
        if status and status != 404:
            print(f"  {path:30s} -> {status}")
            if text and len(text) < 500:
                print(f"    响应: {text[:200]}")
            found_apis.append((path, status, text))
        elif status == 404:
            pass  # 不显示404
        else:
            print(f"  {path:30s} -> 错误: {text}")
    
    print()
    print(f"=== 找到 {len(found_apis)} 个可用API ===")
    for path, status, text in found_apis:
        print(f"  {path} -> {status}")
    
    print()
    print("=== 测试完成 ===")

if __name__ == "__main__":
    main()
