# -*- coding: utf-8 -*-
"""测试更多API路径"""
import urllib.request
import urllib.error
import json
import time
import re

API_URL = "http://127.0.0.1:18111"
ADMIN_TOKEN = "adm_1e3178c6770ceaaa2a63ed44e20a17e4"

def call_api(path, method="GET", data=None):
    """调用API接口"""
    url = f"{API_URL}{path}"
    try:
        headers = {
            "X-Admin-Token": ADMIN_TOKEN,
            "X-Admin-Actor": "gmtool",
        }
        
        if method != "GET" and method != "HEAD":
            headers["Content-Type"] = "application/json"
            op = f"{method} {path.split('?')[0]}"
            headers["X-Admin-Confirm"] = op
            safe_op = re.sub(r'[^a-z0-9]+', '-', op.lower()).strip('-')
            headers["X-Admin-Idempotency-Key"] = f"{safe_op}-{int(time.time())}-{id(time)}"
        
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
    print("=== 测试更多API路径 ===")
    print()
    
    # 测试/debug/路径下的API
    print("=== /debug/ 路径下的API ===")
    debug_paths = [
        "/debug/adapters",
        "/debug/audit",
        "/debug/bilog",
        "/debug/framework",
        "/debug/hotupdate",
        "/debug/i18n",
        "/debug/lifecycle",
        "/debug/logiclog",
        "/debug/metrics",
        "/debug/moderation",
        "/debug/readiness",
        "/debug/rpc",
        "/debug/session-contract",
        "/debug/statesync",
    ]
    
    for path in debug_paths:
        status, text = call_api(path)
        if status and status != 404:
            print(f"  {path:40s} -> {status}")
            if text and len(text) < 300:
                print(f"    响应: {text[:200]}")
        elif status == 404:
            print(f"  {path:40s} -> 404 (不存在)")
        else:
            print(f"  {path:40s} -> 错误: {text}")
    print()
    
    # 测试/gateway/路径下的API
    print("=== /gateway/ 路径下的API ===")
    gateway_paths = [
        "/gateway/push",
        "/gateway/drain",
        "/gateway/session/kick",
        "/gateway/backends",
        "/gateway/presence",
        "/gateway/sessions",
        "/gateway/transports",
    ]
    
    for path in gateway_paths:
        status, text = call_api(path)
        if status and status != 404:
            print(f"  {path:40s} -> {status}")
            if text and len(text) < 300:
                print(f"    响应: {text[:200]}")
        elif status == 404:
            print(f"  {path:40s} -> 404 (不存在)")
        else:
            print(f"  {path:40s} -> 错误: {text}")
    print()
    
    # 测试/accountcenter/路径下的API
    print("=== /accountcenter/ 路径下的API ===")
    account_paths = [
        "/accountcenter/shards",
        "/accountcenter/gates",
        "/accountcenter/login",
        "/accountcenter/bind",
        "/accountcenter/ban",
        "/accountcenter/allow",
    ]
    
    for path in account_paths:
        status, text = call_api(path)
        if status and status != 404:
            print(f"  {path:40s} -> {status}")
            if text and len(text) < 300:
                print(f"    响应: {text[:200]}")
        elif status == 404:
            print(f"  {path:40s} -> 404 (不存在)")
        else:
            print(f"  {path:40s} -> 错误: {text}")
    print()
    
    # 测试/logic/路径下的API
    print("=== /logic/ 路径下的API ===")
    logic_paths = [
        "/logic/accounts",
        "/logic/handlers",
        "/logic/idempotency",
        "/logic/notice",
        "/logic/notice/announcements",
        "/logic/notice/publish",
        "/logic/ops/bans",
        "/logic/ops/events/replay",
        "/logic/ops/leaderboard",
        "/logic/ops/leaderboard/repair",
        "/logic/ops/profile/repair",
        "/logic/playerstore",
        "/logic/playerstore/deadletters",
        "/logic/playerstore/deadletters/requeue",
    ]
    
    for path in logic_paths:
        status, text = call_api(path)
        if status and status != 404:
            print(f"  {path:40s} -> {status}")
            if text and len(text) < 300:
                print(f"    响应: {text[:200]}")
        elif status == 404:
            print(f"  {path:40s} -> 404 (不存在)")
        else:
            print(f"  {path:40s} -> 错误: {text}")
    print()
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    main()
