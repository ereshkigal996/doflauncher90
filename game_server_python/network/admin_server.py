"""
HTTP管理服务器模块
实现服务端的HTTP管理接口，包括账号绑定、状态查询等
"""

import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any


class AdminRequestHandler(BaseHTTPRequestHandler):
    """管理请求处理器"""
    
    # 类变量，用于访问服务端状态
    server_instance = None
    
    def log_message(self, format, *args):
        """重写日志方法，减少输出"""
        pass
    
    def _send_json_response(self, status_code: int, data: Dict[str, Any]):
        """发送JSON响应"""
        response = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)
    
    def _verify_admin_token(self) -> bool:
        """验证管理员令牌"""
        if not self.server_instance:
            return False
        
        admin_token = self.server_instance.admin_token
        if not admin_token:
            return True  # 如果没有设置令牌，允许访问
        
        token = self.headers.get('X-Admin-Token', '')
        return token == admin_token
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == '/ready' or self.path == '/health':
            # 服务端就绪检查
            self._send_json_response(200, {
                'status': 'ok',
                'ready': True,
                'version': self.server_instance.version if self.server_instance else 'unknown',
                'timestamp': int(time.time())
            })
        elif self.path == '/status':
            # 服务端状态
            if self.server_instance:
                self._send_json_response(200, self.server_instance.get_status())
            else:
                self._send_json_response(500, {'error': 'server not initialized'})
        else:
            self._send_json_response(404, {'error': 'not found'})
    
    def do_POST(self):
        """处理POST请求"""
        if self.path == '/local/client-account':
            # 客户端账号绑定
            self._handle_client_account_bind()
        else:
            self._send_json_response(404, {'error': 'not found'})
    
    def _handle_client_account_bind(self):
        """处理客户端账号绑定"""
        # 验证管理员令牌
        if not self._verify_admin_token():
            self._send_json_response(401, {'error': 'invalid admin token'})
            return
        
        # 读取请求体
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
        except Exception as e:
            self._send_json_response(400, {'error': f'invalid request body: {str(e)}'})
            return
        
        # 验证参数
        pid = data.get('pid')
        account_id = data.get('account_id')
        
        if not pid or not account_id:
            self._send_json_response(400, {'error': 'pid and account_id are required'})
            return
        
        # 绑定客户端账号
        if self.server_instance:
            success = self.server_instance.bind_client_account(pid, account_id)
            if success:
                print(f"[Admin] 客户端账号绑定成功: PID={pid}, AccountID={account_id}")
                self._send_json_response(200, {
                    'status': 'ok',
                    'pid': pid,
                    'account_id': account_id
                })
            else:
                self._send_json_response(500, {'error': 'bind failed'})
        else:
            self._send_json_response(500, {'error': 'server not initialized'})


class AdminHTTPServer:
    """HTTP管理服务器"""
    
    def __init__(self, host: str, port: int, admin_token: str = "", version: str = "0.1.0"):
        self.host = host
        self.port = port
        self.admin_token = admin_token
        self.version = version
        self.server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self.running = False
        
        # 客户端账号绑定映射: PID -> account_id
        self.client_accounts: Dict[int, str] = {}
        self._lock = threading.Lock()
        
        # 设置处理器的服务端实例
        AdminRequestHandler.server_instance = self
    
    def start(self) -> bool:
        """启动HTTP服务器"""
        try:
            self.server = HTTPServer((self.host, self.port), AdminRequestHandler)
            self.running = True
            
            self._thread = threading.Thread(target=self._serve_forever, daemon=True)
            self._thread.start()
            
            print(f"[AdminHTTP] 管理服务器启动成功: {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"[AdminHTTP] 管理服务器启动失败: {e}")
            return False
    
    def _serve_forever(self):
        """服务循环"""
        try:
            self.server.serve_forever()
        except Exception as e:
            if self.running:
                print(f"[AdminHTTP] 服务器异常: {e}")
    
    def stop(self):
        """停止HTTP服务器"""
        self.running = False
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
        print("[AdminHTTP] 管理服务器已停止")
    
    def bind_client_account(self, pid: int, account_id: str) -> bool:
        """绑定客户端账号"""
        try:
            with self._lock:
                self.client_accounts[pid] = account_id
            return True
        except Exception as e:
            print(f"[AdminHTTP] 绑定客户端账号失败: {e}")
            return False
    
    def get_client_account(self, pid: int) -> Optional[str]:
        """获取客户端账号ID"""
        with self._lock:
            return self.client_accounts.get(pid)
    
    def unbind_client_account(self, pid: int):
        """解绑客户端账号"""
        with self._lock:
            self.client_accounts.pop(pid, None)
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务端状态"""
        with self._lock:
            return {
                'version': self.version,
                'running': self.running,
                'bound_clients': len(self.client_accounts),
                'client_accounts': {str(k): v for k, v in self.client_accounts.items()}
            }


# 单例模式
_admin_server: Optional[AdminHTTPServer] = None


def init_admin_server(host: str, port: int, admin_token: str = "", version: str = "0.1.0") -> AdminHTTPServer:
    """初始化管理服务器"""
    global _admin_server
    _admin_server = AdminHTTPServer(host, port, admin_token, version)
    return _admin_server


def get_admin_server() -> Optional[AdminHTTPServer]:
    """获取管理服务器实例"""
    return _admin_server
