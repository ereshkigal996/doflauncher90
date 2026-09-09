# -*- coding: utf-8 -*-
"""测试服务端管理API的具体功能"""
import urllib.request
import urllib.error
import json

API_URL = "http://127.0.0.1:18111"
ADMIN_TOKEN = "adm_1e3178c6770ceaaa2a63ed44e20a17e4"
ACCOUNT_ID = "dnf:43ca6920ecea925361055c8e9463fd15"

def call_api(path, method="GET", data=None):
    """调用API接口"""
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
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, response.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None, str(e)

def main():
    print("=== 测试服务端管理API ===")
    print(f"API URL: {API_URL}")
    print(f"账号ID: {ACCOUNT_ID}")
    print()
    
    # 1. 测试健康检查
    print("=== 1. 健康检查 ===")
    status, text = call_api("/healthz")
    print(f"状态码: {status}")
    print(f"响应: {text[:500]}")
    print()
    
    # 2. 测试账号列表
    print("=== 2. 账号列表 ===")
    status, text = call_api("/logic/accounts")
    print(f"状态码: {status}")
    print(f"响应: {text[:1000]}")
    print()
    
    # 3. 测试存储对象读取（尝试读取账号数据）
    print("=== 3. 存储对象读取 ===")
    data = {
        "keys": [
            {"collection": "account", "key": ACCOUNT_ID}
        ]
    }
    status, text = call_api("/storage/objects/read", method="POST", data=data)
    print(f"状态码: {status}")
    print(f"响应: {text[:1000]}")
    print()
    
    # 4. 测试存储对象读取（尝试读取全局数据）
    print("=== 4. 存储对象读取（全局）===")
    data = {
        "keys": [
            {"collection": "global", "key": "motd"}
        ]
    }
    status, text = call_api("/storage/objects/read", method="POST", data=data)
    print(f"状态码: {status}")
    print(f"响应: {text[:500]}")
    print()
    
    # 5. 测试网关会话
    print("=== 5. 网关会话 ===")
    status, text = call_api("/gateway/sessions")
    print(f"状态码: {status}")
    print(f"响应: {text[:500]}")
    print()
    
    # 6. 测试网关存在
    print("=== 6. 网关存在 ===")
    status, text = call_api("/gateway/presence")
    print(f"状态码: {status}")
    print(f"响应: {text[:500]}")
    print()
    
    # 7. 测试调试配置
    print("=== 7. 调试配置 ===")
    status, text = call_api("/debug/config")
    print(f"状态码: {status}")
    print(f"响应: {text[:1000]}")
    print()
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    main()
