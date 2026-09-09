"""
游戏服务器模块
实现DNF游戏服务器（频道端口），处理客户端游戏连接、数据包路由等
"""

import socket
import threading
import time
import logging
from typing import Optional, Dict, List, Callable, Tuple
from dataclasses import dataclass, field

from protocol.channel_packet import (
    ChannelPacket,
    ChannelHeader,
    build_channel_packet,
    parse_channel_packet,
    parse_channel_packet_unchecked,
    ChannelHeaderSize,
    DefaultChannelClassification,
)
from protocol.dnf_crypto import encrypt_channel_data, decrypt_channel_data
from protocol.dnf_checksum import checksum_range
from game.bootstrap import GameBootstrap, UpperMsg
from game.character import CharacterManager, MemoryCharacterRepository


# 日志
logger = logging.getLogger(__name__)


# 游戏流数据包类型
class GameStreamKind:
    """游戏流数据包类型"""
    Transport = 0  # 传输层（frame_v1）
    Upper = 1      # 上层包（13字节raw upper）
    Legacy = 2     # 旧版包
    Dproto = 3     # DPROTO原生协议包


@dataclass
class GameStreamPacket:
    """游戏流数据包"""
    kind: int
    data: bytes


@dataclass
class GameChannel:
    """游戏频道"""
    id: int = 0
    name: str = ""
    port: int = 0
    max_users: int = 0
    current_users: int = 0
    type: str = ""


@dataclass
class GameSession:
    """游戏会话"""
    conn: socket.socket
    addr: tuple
    session_id: str = ""
    account_id: str = ""
    client_pid: int = 0
    channel: Optional[GameChannel] = None
    sequence: int = 0
    upper_seq: int = 0
    connected: bool = True
    
    # 游戏状态
    character_generation: int = 0
    selected_character_id: int = 0
    roster_requested: bool = False
    
    # 缓冲区
    buffer: bytes = b""


class GameServer:
    """
    DNF游戏服务器
    
    监听频道游戏端口，处理客户端游戏连接
    """
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        aes_key: str = "0123456789abcdef",
        server_ip: str = "127.0.0.1",
    ):
        """
        初始化游戏服务器
        
        Args:
            host: 监听地址
            aes_key: AES加密密钥
            server_ip: 服务器IP
        """
        self.host = host
        self.aes_key = aes_key
        self.server_ip = server_ip
        
        self.server_sockets: Dict[int, socket.socket] = {}  # port -> socket
        self.running = False
        self.sessions: Dict[str, GameSession] = {}
        self.channels: List[GameChannel] = []
        self._lock = threading.Lock()
        
        # 游戏引导模块
        self.character_manager: CharacterManager = None
        self.bootstrap: GameBootstrap = None
        
        # 会话ID计数器
        self._session_counter = 0
    
    def start(self):
        """启动游戏服务器"""
        if self.running:
            logger.warning("Game server is already running")
            return
        
        # 初始化角色管理器和游戏引导模块
        if not self.character_manager:
            self.character_manager = CharacterManager(MemoryCharacterRepository())
        if not self.bootstrap:
            self.bootstrap = GameBootstrap(
                server_ip=self.server_ip,
                character_manager=self.character_manager,
            )
        
        self.running = True
        logger.info("Game server starting...")
        
        # 为每个频道启动监听
        with self._lock:
            channels = list(self.channels)
        
        for channel in channels:
            self._start_listener(channel)
        
        logger.info(f"Game server started, listening on {len(channels)} ports")
    
    def stop(self):
        """停止游戏服务器"""
        self.running = False
        
        # 关闭所有会话
        with self._lock:
            for session in self.sessions.values():
                try:
                    session.conn.close()
                except Exception:
                    pass
            self.sessions.clear()
        
        # 关闭所有服务器socket
        for port, sock in self.server_sockets.items():
            try:
                sock.close()
            except Exception:
                pass
        self.server_sockets.clear()
        
        logger.info("Game server stopped")
    
    def add_channel(self, channel: GameChannel):
        """添加游戏频道"""
        with self._lock:
            self.channels.append(channel)
            
            # 如果服务器已在运行，启动新的监听器
            if self.running:
                self._start_listener(channel)
    
    def remove_channel(self, channel_id: int):
        """移除游戏频道"""
        with self._lock:
            channel = next((c for c in self.channels if c.id == channel_id), None)
            if channel:
                self.channels.remove(channel)
                
                # 关闭对应的监听器
                if channel.port in self.server_sockets:
                    try:
                        self.server_sockets[channel.port].close()
                    except Exception:
                        pass
                    del self.server_sockets[channel.port]
    
    def _start_listener(self, channel: GameChannel):
        """启动频道监听器"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, channel.port))
            sock.listen(128)
            
            self.server_sockets[channel.port] = sock
            
            # 启动接受连接线程
            thread = threading.Thread(
                target=self._accept_loop,
                args=(sock, channel),
                daemon=True,
            )
            thread.start()
            
            logger.info(f"Game channel listener started: {channel.name} on port {channel.port}")
            
        except Exception as e:
            logger.error(f"Failed to start game channel listener for port {channel.port}: {e}")
    
    def _accept_loop(self, server_socket: socket.socket, channel: GameChannel):
        """接受连接循环"""
        while self.running:
            try:
                conn, addr = server_socket.accept()
                conn.settimeout(60)  # 60秒超时
                
                # 创建会话
                session_id = self._next_session_id()
                session = GameSession(
                    conn=conn,
                    addr=addr,
                    session_id=session_id,
                    channel=channel,
                )
                
                with self._lock:
                    self.sessions[session_id] = session
                
                logger.info(
                    f"Game connection accepted: {addr} "
                    f"(channel={channel.name}, session={session_id})"
                )
                
                # 启动会话处理线程
                thread = threading.Thread(
                    target=self._handle_session,
                    args=(session,),
                    daemon=True,
                )
                thread.start()
                
            except socket.error as e:
                if self.running:
                    logger.error(f"Game accept error: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected game accept error: {e}")
    
    def _handle_session(self, session: GameSession):
        """处理游戏会话"""
        try:
            # 发送游戏连接引导包
            self._send_connection_bootstrap(session)
            
            # 主循环
            buffer = b""
            chunk = bytearray(4096)
            
            while session.connected and self.running:
                try:
                    n = session.conn.recv_into(chunk)
                    if n == 0:
                        break
                    
                    data = bytes(chunk[:n])
                    logger.debug(f"Received game data: {len(data)} bytes from {session.addr}")
                    
                    buffer += data
                    
                    # 分割游戏流数据包
                    packets, buffer = self._split_game_stream(buffer)
                    
                    # 处理每个数据包
                    for packet in packets:
                        self._handle_game_packet(session, packet)
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Game session error: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Game session handling error: {e}")
        finally:
            self._cleanup_session(session)
    
    def _send_connection_bootstrap(self, session: GameSession):
        """发送游戏连接引导包"""
        try:
            # 使用游戏引导模块发送初始CHANNELINFO通知
            if self.bootstrap and session.channel:
                notice = self.bootstrap.send_initial_notice(
                    session_id=session.session_id,
                    channel_id=session.channel.id,
                    channel_port=session.channel.port,
                )
                session.conn.sendall(notice)
                logger.debug(f"Sent connection bootstrap to {session.addr}")
                
        except Exception as e:
            logger.error(f"Failed to send connection bootstrap: {e}")
    
    def _build_bootstrap_data(self, session: GameSession) -> Optional[bytes]:
        """构建引导数据"""
        # 简化版本，实际需要根据DPROTO协议构建
        # 这里返回一个简单的确认包
        return b"\x00" * 16
    
    def _split_game_stream(self, buffer: bytes) -> Tuple[List[GameStreamPacket], bytes]:
        """
        分割游戏流数据包
        
        Args:
            buffer: 输入缓冲区
            
        Returns:
            (数据包列表, 剩余缓冲区)
        """
        packets = []
        
        while len(buffer) >= 4:
            # 尝试识别数据包类型
            # 1. 检查是否是frame_v1（魔数0x5047）
            if buffer[0] == 0x47 and buffer[1] == 0x50:  # "GP"小端
                if len(buffer) >= 32:
                    body_size = int.from_bytes(buffer[24:28], 'little')
                    total_size = 32 + body_size
                    if len(buffer) >= total_size:
                        packets.append(GameStreamPacket(
                            kind=GameStreamKind.Transport,
                            data=buffer[:total_size],
                        ))
                        buffer = buffer[total_size:]
                        continue
                break
            
            # 2. 检查是否是13字节raw upper包
            if buffer[0] == DefaultChannelClassification:
                if len(buffer) >= 13:
                    total_size = int.from_bytes(buffer[3:7], 'little')
                    if total_size >= 13 and len(buffer) >= total_size:
                        packets.append(GameStreamPacket(
                            kind=GameStreamKind.Upper,
                            data=buffer[:total_size],
                        ))
                        buffer = buffer[total_size:]
                        continue
                break
            
            # 3. 检查是否是旧版包（前2字节大端长度）
            legacy_length = int.from_bytes(buffer[0:2], 'big')
            if 4 <= legacy_length <= 4096 and len(buffer) >= legacy_length + 4:
                total_size = 4 + legacy_length
                packets.append(GameStreamPacket(
                    kind=GameStreamKind.Legacy,
                    data=buffer[:total_size],
                ))
                buffer = buffer[total_size:]
                continue
            
            # 无法识别，跳过1字节
            buffer = buffer[1:]
        
        return packets, buffer
    
    def _handle_game_packet(self, session: GameSession, packet: GameStreamPacket):
        """处理游戏数据包"""
        try:
            if packet.kind == GameStreamKind.Transport:
                self._handle_transport_packet(session, packet.data)
            elif packet.kind == GameStreamKind.Upper:
                self._handle_upper_packet(session, packet.data)
            elif packet.kind == GameStreamKind.Legacy:
                self._handle_legacy_packet(session, packet.data)
            elif packet.kind == GameStreamKind.Dproto:
                self._handle_dproto_packet(session, packet.data)
            else:
                logger.debug(f"Unknown game packet kind: {packet.kind}")
        except Exception as e:
            logger.error(f"Failed to handle game packet: {e}")
    
    def _handle_transport_packet(self, session: GameSession, data: bytes):
        """处理传输层数据包（frame_v1）"""
        # 简化处理，实际需要解析frame_v1并解密
        logger.debug(f"Handling transport packet: {len(data)} bytes")
    
    def _handle_upper_packet(self, session: GameSession, data: bytes):
        """处理上层数据包（13字节raw upper）"""
        try:
            packet = parse_channel_packet_unchecked(data)
            msg_id = packet.header.msg_id
            
            logger.debug(
                f"Handling upper packet: msg_id=0x{msg_id:04x}, "
                f"seq={packet.header.seq}, body_size={len(packet.body)}"
            )
            
            # 根据消息ID路由处理
            # 这里是简化版本，实际需要大量的消息处理
            self._route_upper_message(session, msg_id, packet.body)
            
        except Exception as e:
            logger.error(f"Failed to handle upper packet: {e}")
    
    def _handle_legacy_packet(self, session: GameSession, data: bytes):
        """处理旧版数据包"""
        logger.debug(f"Handling legacy packet: {len(data)} bytes")
    
    def _handle_dproto_packet(self, session: GameSession, data: bytes):
        """处理DPROTO原生协议数据包"""
        logger.debug(f"Handling dproto packet: {len(data)} bytes")
    
    def _route_upper_message(self, session: GameSession, msg_id: int, body: bytes):
        """
        路由上层消息
        
        Args:
            session: 游戏会话
            msg_id: 消息ID
            body: 消息体
        """
        # 使用游戏引导模块处理消息
        if self.bootstrap and session.channel:
            responses = self.bootstrap.handle_packet(
                session_id=session.session_id,
                msg_id=msg_id,
                body=body,
                channel_id=session.channel.id,
                channel_port=session.channel.port,
                account_id=session.account_id,
            )
            
            # 发送响应
            for response in responses:
                try:
                    session.conn.sendall(response)
                except Exception as e:
                    logger.error(f"Failed to send response: {e}")
                    session.connected = False
                    return
        
        logger.debug(f"Routing upper message: msg_id=0x{msg_id:04x}")
    
    def _send_upper_packet(self, session: GameSession, msg_id: int, body: bytes):
        """发送上层数据包"""
        try:
            packet = build_channel_packet(msg_id, body, session.upper_seq)
            session.upper_seq = (session.upper_seq + 1) & 0xFFFF
            
            session.conn.sendall(packet)
            
            logger.debug(
                f"Sent upper packet: msg_id=0x{msg_id:04x}, "
                f"seq={session.upper_seq - 1}, body_size={len(body)}"
            )
        except Exception as e:
            logger.error(f"Failed to send upper packet: {e}")
            session.connected = False
    
    def _next_session_id(self) -> str:
        """生成下一个会话ID"""
        self._session_counter += 1
        return f"game-{self._session_counter}"
    
    def _cleanup_session(self, session: GameSession):
        """清理会话"""
        session.connected = False
        
        try:
            session.conn.close()
        except Exception:
            pass
        
        with self._lock:
            if session.session_id in self.sessions:
                del self.sessions[session.session_id]
        
        logger.info(f"Game connection closed: {session.addr} (session={session.session_id})")
