# -*- coding: utf-8 -*-
"""测试原版GM工具的黑钻API"""
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
    print("=== 测试原版GM工具的黑钻API ===")
    print(f"API URL: {API_URL}")
    print()
    
    # 1. 先获取角色列表
    print("=== 1. 获取角色列表 ===")
    # 尝试不同的查询方式
    test_queries = [
        {"account": "", "name": ""},
        {"account_id": "", "character_name": ""},
        {"query": ""},
        {"search": ""},
    ]
    
    for i, query in enumerate(test_queries):
        status, text = call_api("/api/characters", method="POST", data=query)
        print(f"  查询方式 {i+1}: {json.dumps(query)}")
        print(f"    状态码: {status}")
        print(f"    响应: {text[:300]}")
        print()
    
    # 2. 测试黑钻API（GET）
    print("=== 2. 测试黑钻API（GET）===")
    status, text = call_api("/api/character/black-diamond")
    print(f"状态码: {status}")
    print(f"响应: {text[:500]}")
    print()
    
    # 3. 测试黑钻API（POST，不带参数）
    print("=== 3. 测试黑钻API（POST，不带参数）===")
    status, text = call_api("/api/character/black-diamond", method="POST", data={})
    print(f"状态码: {status}")
    print(f"响应: {text[:500]}")
    print()
    
    # 4. 测试黑钻API（POST，带角色ID）
    print("=== 4. 测试黑钻API（POST，带角色ID）===")
    test_data = [
        {"character_id": 1},
        {"characterId": 1},
        {"id": 1},
        {"character_id": "1"},
    ]
    
    for i, data in enumerate(test_data):
        status, text = call_api("/api/character/black-diamond", method="POST", data=data)
        print(f"  测试数据 {i+1}: {json.dumps(data)}")
        print(f"    状态码: {status}")
        print(f"    响应: {text[:300]}")
        print()
    
    # 5. 测试钱包查询API
    print("=== 5. 测试钱包查询API ===")
    wallet_data = [
        {"character_id": 1},
        {"characterId": 1},
        {"role": "死亡左轮"},
        {"character_name": "死亡左轮"},
    ]
    
    for i, data in enumerate(wallet_data):
        status, text = call_api("/api/wallet/query", method="POST", data=data)
        print(f"  测试数据 {i+1}: {json.dumps(data)}")
        print(f"    状态码: {status}")
        print(f"    响应: {text[:300]}")
        print()
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    main()
