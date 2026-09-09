# -*- coding: utf-8 -*-
"""测试服务端管理API的子路径"""
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
    print("=== 测试服务端管理API子路径 ===")
    print(f"API URL: {API_URL}/admin")
    print()
    
    # 先获取/admin的响应，看看有没有API文档
    print("=== /admin 响应 ===")
    status, text = test_api("/admin")
    print(f"状态码: {status}")
    print(f"响应: {text[:1000]}")
    print()
    
    # 测试/admin/路径下的子路径
    test_paths = [
        "/admin/health",
        "/admin/status",
        "/admin/account",
        "/admin/accounts",
        "/admin/character",
        "/admin/characters",
        "/admin/premium",
        "/admin/vip",
        "/admin/member",
        "/admin/black-dragon",
        "/admin/blackdragon",
        "/admin/service",
        "/admin/services",
        "/admin/cera",
        "/admin/gold",
        "/admin/item",
        "/admin/items",
        "/admin/mail",
        "/admin/mails",
        "/admin/api",
        "/admin/api/",
        "/admin/v1",
        "/admin/v1/",
        "/admin/v1/account",
        "/admin/v1/accounts",
        "/admin/v1/character",
        "/admin/v1/characters",
        "/admin/v1/premium",
        "/admin/v1/cera",
        "/admin/v1/gold",
        "/admin/v1/item",
        "/admin/v1/items",
        "/admin/v1/mail",
        "/admin/v1/mails",
        "/admin/user",
        "/admin/users",
        "/admin/config",
        "/admin/settings",
        "/admin/info",
        "/admin/version",
        "/admin/help",
        "/admin/docs",
        "/admin/swagger",
        "/admin/openapi",
    ]
    
    print("=== 测试API子路径 ===")
    found_apis = []
    for path in test_paths:
        status, text = test_api(path)
        if status and status != 404:
            print(f"  {path:40s} -> {status}")
            if text and len(text) < 500:
                print(f"    响应: {text[:200]}")
            found_apis.append((path, status, text))
        elif status == 404:
            pass  # 不显示404
        else:
            print(f"  {path:40s} -> 错误: {text}")
    
    print()
    print(f"=== 找到 {len(found_apis)} 个可用API ===")
    for path, status, text in found_apis:
        print(f"  {path} -> {status}")
    
    print()
    print("=== 测试完成 ===")

if __name__ == "__main__":
    main()
