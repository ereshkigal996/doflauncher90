"""
网络服务模块
实现基础的TCP服务器，包括频道监听和管理监听
"""

import socket
import threading
import time
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class ClientConnection:
    """客户端连接"""
    conn: socket.socket
    addr: tuple
    connected: bool = True
    connect_time: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    user_data: Dict[str, Any] = field(default_factory=dict)
    
    def send(self, data: bytes) -> bool:
        """发送数据"""
        try:
            self.conn.sendall(data)
            self.last_active = time.time()
            return True
        except Exception as e:
            print(f"[ClientConnection] 发送失败: {e}")
            self.connected = False
            return False
    
    def recv(self, bufsize: int = 4096) -> Optional[bytes]:
        """接收数据"""
        try:
            data = self.conn.recv(bufsize)
            if not data:
                self.connected = False
                return None
            self.last_active = time.time()
            return data
        except socket.timeout:
            return b""
        except Exception as e:
            print(f"[ClientConnection] 接收失败: {e}")
            self.connected = False
            return None
    
    def close(self):
        """关闭连接"""
        try:
            self.connected = False
            self.conn.close()
        except Exception:
            pass


class BaseTCPServer:
    """基础TCP服务器"""
    
    def __init__(self, host: str, port: int, name: str = "TCPServer"):
        self.host = host
        self.port = port
        self.name = name
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.clients: List[ClientConnection] = []
        self._lock = threading.Lock()
        self._accept_thread: Optional[threading.Thread] = None
        
        # 回调函数
        self.on_client_connect: Optional[Callable[[ClientConnection], None]] = None
        self.on_client_disconnect: Optional[Callable[[ClientConnection], None]] = None
        self.on_data_received: Optional[Callable[[ClientConnection, bytes], None]] = None
    
    def start(self) -> bool:
        """启动服务器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(128)
            self.server_socket.settimeout(1.0)
            
            self.running = True
            self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self._accept_thread.start()
            
            print(f"[{self.name}] 服务器启动成功: {self.host}:{self.port}")
            return True
            
        except Exception as e:
            print(f"[{self.name}] 服务器启动失败: {e}")
            return False
    
    def _accept_loop(self):
        """接受连接循环"""
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                conn.settimeout(0.5)
                
                client = ClientConnection(conn=conn, addr=addr)
                
                with self._lock:
                    self.clients.append(client)
                
                print(f"[{self.name}] 客户端连接: {addr} (当前连接数: {len(self.clients)})")
                
                # 触发连接回调
                if self.on_client_connect:
                    try:
                        self.on_client_connect(client)
                    except Exception as e:
                        print(f"[{self.name}] 连接回调异常: {e}")
                
                # 启动客户端处理线程
                thread = threading.Thread(
                    target=self._client_loop,
                    args=(client,),
                    daemon=True
                )
                thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[{self.name}] 接受连接异常: {e}")
    
    def _client_loop(self, client: ClientConnection):
        """客户端处理循环"""
        while self.running and client.connected:
            try:
                data = client.recv(4096)
                if data is None:
                    break
                if not data:
                    continue
                
                # 触发数据接收回调
                if self.on_data_received:
                    try:
                        self.on_data_received(client, data)
                    except Exception as e:
                        print(f"[{self.name}] 数据处理异常: {e}")
                
            except Exception as e:
                print(f"[{self.name}] 客户端处理异常: {e}")
                break
        
        # 客户端断开
        self._remove_client(client)
    
    def _remove_client(self, client: ClientConnection):
        """移除客户端"""
        with self._lock:
            if client in self.clients:
                self.clients.remove(client)
        
        client.close()
        
        print(f"[{self.name}] 客户端断开: {client.addr} (当前连接数: {len(self.clients)})")
        
        # 触发断开回调
        if self.on_client_disconnect:
            try:
                self.on_client_disconnect(client)
            except Exception as e:
                print(f"[{self.name}] 断开回调异常: {e}")
    
    def broadcast(self, data: bytes) -> int:
        """广播数据到所有客户端"""
        count = 0
        with self._lock:
            for client in self.clients:
                if client.connected and client.send(data):
                    count += 1
        return count
    
    def get_client_count(self) -> int:
        """获取当前连接数"""
        with self._lock:
            return len([c for c in self.clients if c.connected])
    
    def stop(self):
        """停止服务器"""
        print(f"[{self.name}] 正在停止服务器...")
        self.running = False
        
        # 关闭所有客户端连接
        with self._lock:
            for client in self.clients:
                client.close()
            self.clients.clear()
        
        # 关闭服务器socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        
        print(f"[{self.name}] 服务器已停止")


class ChannelServer(BaseTCPServer):
    """频道服务器（游戏客户端连接）"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 7001):
        super().__init__(host, port, name="ChannelServer")


class AdminServer(BaseTCPServer):
    """管理服务器（GM工具、管理工具连接）"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 18111):
        super().__init__(host, port, name="AdminServer")
        self.admin_token = ""
    
    def verify_token(self, token: str) -> bool:
        """验证管理令牌"""
        if not self.admin_token:
            return True  # 未设置令牌时允许所有连接
        return token == self.admin_token


class NetworkManager:
    """网络管理器"""
    
    def __init__(self):
        self.channel_server: Optional[ChannelServer] = None
        self.admin_server: Optional[AdminServer] = None
        self._running = False
    
    def init_from_config(self, config) -> bool:
        """从配置初始化网络服务"""
        server_config = config.server
        
        # 解析频道监听地址
        channel_parts = server_config.channel_listen.split(':')
        channel_host = channel_parts[0] if len(channel_parts) > 0 else "127.0.0.1"
        channel_port = int(channel_parts[1]) if len(channel_parts) > 1 else 7001
        
        # 解析管理监听地址
        admin_parts = server_config.admin_listen.split(':')
        admin_host = admin_parts[0] if len(admin_parts) > 0 else "127.0.0.1"
        admin_port = int(admin_parts[1]) if len(admin_parts) > 1 else 18111
        
        # 创建服务器
        self.channel_server = ChannelServer(channel_host, channel_port)
        self.admin_server = AdminServer(admin_host, admin_port)
        self.admin_server.admin_token = server_config.admin_token
        
        print(f"[NetworkManager] 网络服务初始化完成")
        print(f"[NetworkManager] 频道服务器: {channel_host}:{channel_port}")
        print(f"[NetworkManager] 管理服务器: {admin_host}:{admin_port}")
        
        return True
    
    def start(self) -> bool:
        """启动所有网络服务"""
        if not self.channel_server or not self.admin_server:
            print("[NetworkManager] 错误: 网络服务未初始化")
            return False
        
        # 启动频道服务器
        if not self.channel_server.start():
            print("[NetworkManager] 频道服务器启动失败")
            return False
        
        # 启动管理服务器
        if not self.admin_server.start():
            print("[NetworkManager] 管理服务器启动失败")
            self.channel_server.stop()
            return False
        
        self._running = True
        print("[NetworkManager] 所有网络服务启动成功")
        return True
    
    def stop(self):
        """停止所有网络服务"""
        print("[NetworkManager] 正在停止所有网络服务...")
        self._running = False
        
        if self.channel_server:
            self.channel_server.stop()
        
        if self.admin_server:
            self.admin_server.stop()
        
        print("[NetworkManager] 所有网络服务已停止")
    
    def is_running(self) -> bool:
        """网络服务是否运行中"""
        return self._running
    
    def get_total_connections(self) -> int:
        """获取总连接数"""
        count = 0
        if self.channel_server:
            count += self.channel_server.get_client_count()
        if self.admin_server:
            count += self.admin_server.get_client_count()
        return count


# 全局网络管理器实例
_network_manager: Optional[NetworkManager] = None


def get_network_manager() -> NetworkManager:
    """获取全局网络管理器实例"""
    global _network_manager
    if _network_manager is None:
        _network_manager = NetworkManager()
    return _network_manager


def init_network(config) -> bool:
    """初始化全局网络服务"""
    global _network_manager
    _network_manager = NetworkManager()
    return _network_manager.init_from_config(config)
