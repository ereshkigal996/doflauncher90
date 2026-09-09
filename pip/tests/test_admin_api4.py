# -*- coding: utf-8 -*-
"""测试其他API路径，并获取/admin页面完整内容"""
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
    print("=== 获取/admin页面完整内容 ===")
    status, text = test_api("/admin")
    print(f"状态码: {status}")
    print(f"内容长度: {len(text)}")
    print()
    print("=== 页面内容（前2000字符）===")
    print(text[:2000])
    print()
    
    # 查找页面中的API相关字符串
    print("=== 查找页面中的API相关字符串 ===")
    api_keywords = ['/api/', 'fetch(', 'axios', 'XMLHttpRequest', 'endpoint', 'apiUrl', 'baseUrl']
    for kw in api_keywords:
        if kw in text:
            print(f"  找到: {kw}")
            # 查找上下文
            idx = text.find(kw)
            start = max(0, idx - 50)
            end = min(len(text), idx + 100)
            print(f"    上下文: ...{text[start:end]}...")
    print()
    
    # 测试其他API路径
    print("=== 测试其他API路径 ===")
    test_paths = [
        "/api",
        "/api/",
        "/api/v1",
        "/api/v1/",
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
        "/api/user",
        "/api/users",
        "/api/config",
        "/api/settings",
        "/api/info",
        "/api/version",
        "/v1",
        "/v1/",
        "/v1/health",
        "/v1/status",
        "/v1/account",
        "/v1/accounts",
        "/v1/character",
        "/v1/characters",
        "/v1/premium",
        "/v1/cera",
        "/v1/gold",
        "/v1/item",
        "/v1/items",
        "/v1/mail",
        "/v1/mails",
        "/health",
        "/status",
        "/info",
        "/version",
    ]
    
    found_apis = []
    for path in test_paths:
        status, text = test_api(path)
        if status and status != 404:
            # 检查是否是JSON响应
            is_json = False
            if text:
                try:
                    json.loads(text)
                    is_json = True
                except:
                    pass
            
            if is_json:
                print(f"  {path:40s} -> {status} (JSON)")
                print(f"    响应: {text[:200]}")
                found_apis.append((path, status, text))
            # 不显示HTML响应（可能是前端路由）
        elif status == 404:
            pass  # 不显示404
        else:
            print(f"  {path:40s} -> 错误: {text}")
    
    print()
    print(f"=== 找到 {len(found_apis)} 个JSON API ===")
    for path, status, text in found_apis:
        print(f"  {path} -> {status}")
    
    print()
    print("=== 测试完成 ===")

if __name__ == "__main__":
    main()
