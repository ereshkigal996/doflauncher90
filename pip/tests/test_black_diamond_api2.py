# -*- coding: utf-8 -*-
"""测试原版GM工具的黑钻API（修正参数）"""
import urllib.request
import urllib.error
import json

API_URL = "http://127.0.0.1:53322"

def call_api(path, method="GET", data=None, params=None):
    """调用API接口"""
    url = f"{API_URL}{path}"
    
    # 添加查询参数
    if params:
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"{url}?{query_string}"
    
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
    print("=== 测试原版GM工具的黑钻API（修正参数）===")
    print(f"API URL: {API_URL}")
    print()
    
    # 1. 获取角色列表（GET方法，带查询参数）
    print("=== 1. 获取角色列表 ===")
    test_params = [
        {"account": ""},
        {"name": ""},
        {"q": ""},
        {"search": ""},
        {"query": ""},
        {"account": "", "name": ""},
    ]
    
    for i, params in enumerate(test_params):
        status, text = call_api("/api/characters", method="GET", params=params)
        print(f"  查询参数 {i+1}: {json.dumps(params)}")
        print(f"    状态码: {status}")
        print(f"    响应: {text[:500]}")
        print()
    
    # 2. 测试黑钻API（POST，characterId为字符串）
    print("=== 2. 测试黑钻API（characterId为字符串）===")
    test_data = [
        {"characterId": "1"},
        {"characterId": "1", "days": 30},
        {"characterId": "1", "duration": 30},
    ]
    
    for i, data in enumerate(test_data):
        status, text = call_api("/api/character/black-diamond", method="POST", data=data)
        print(f"  测试数据 {i+1}: {json.dumps(data)}")
        print(f"    状态码: {status}")
        print(f"    响应: {text[:500]}")
        print()
    
    # 3. 测试钱包查询API（尝试不同的参数名）
    print("=== 3. 测试钱包查询API ===")
    wallet_data = [
        {"characterId": "1"},
        {"character_id": "1"},
        {"id": "1"},
        {"name": "死亡左轮"},
        {"characterName": "死亡左轮"},
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
