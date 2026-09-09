"""
频道服务器模块
实现DNF频道服务器（端口7001），处理客户端连接、频道列表、脚本下发等
"""

import socket
import threading
import time
import logging
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field

from protocol.channel_packet import (
    ChannelPacket,
    ChannelHeader,
    build_channel_packet,
    parse_channel_packet,
    parse_channel_packet_unchecked,
    is_dof_login_preface_prefix,
    is_dof_channel_probe_prefix,
    is_dof_ask_channel_prefix,
    build_dof_login_ack,
    build_legacy_channel_packet,
    ChannelHeaderSize,
    LegacyChannelHeaderSize,
    DofLoginPrefaceSize,
    DofAskChannelSize,
    DefaultChannelClassification,
)
from protocol.dnf_crypto import encrypt_channel_data, decrypt_channel_data
from protocol.dnf_checksum import checksum_range


# 日志
logger = logging.getLogger(__name__)


# 频道消息ID（从dnfenum提取的关键值）
class ChannelMsg:
    """频道消息ID枚举"""
    # 客户端 -> 服务端
    MsgCSConnect = 0x0001
    MsgCSAskChannelInfoNew = 0x0002
    MsgCSUpdateChannelInfo = 0x0003
    MsgCSCheckScript = 0x0004
    MsgCSGetScript = 0x0005
    
    # 服务端 -> 客户端
    MsgSCConnect = 0x0001
    MsgSCAskChannelInfo = 0x0002
    MsgSCCheckScript = 0x0004
    MsgSCGetScript = 0x0005


# 旧版消息ID
class LegacyMsg:
    """旧版消息ID枚举"""
    LegacyMsgChannelInfo = 0x0002
    LegacyMsgDofScript = 0x0005


@dataclass
class ChannelInfo:
    """频道信息"""
    id: int = 0
    name: str = ""
    port: int = 0
    max_users: int = 0
    current_users: int = 0


@dataclass
class ChannelSession:
    """频道会话"""
    conn: socket.socket
    addr: tuple
    session_id: str = ""
    seq: int = 0
    packet_seq: int = 0
    script_sent: bool = False
    close_after_bootstrap: bool = False
    connected: bool = True


class ChannelServer:
    """
    DNF频道服务器
    
    监听7001端口，处理客户端连接、频道列表、脚本下发等
    """
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 7001,
        aes_key: str = "0123456789abcdef",
        server_ip: str = "127.0.0.1",
        channel_info_file: Optional[str] = None,
        script_version: str = "1.0.0",
    ):
        """
        初始化频道服务器
        
        Args:
            host: 监听地址
            port: 监听端口
            aes_key: AES加密密钥
            server_ip: 服务器IP（用于频道信息）
            channel_info_file: 频道信息脚本文件路径
            script_version: 脚本版本
        """
        self.host = host
        self.port = port
        self.aes_key = aes_key
        self.server_ip = server_ip
        self.channel_info_file = channel_info_file
        self.script_version = script_version
        
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.sessions: Dict[str, ChannelSession] = {}
        self.channels: List[ChannelInfo] = []
        self._lock = threading.Lock()
        
        # 会话ID计数器
        self._session_counter = 0
        
        # 频道脚本缓存
        self._channel_script: Optional[bytes] = None
    
    def start(self):
        """启动频道服务器"""
        if self.running:
            logger.warning("Channel server is already running")
            return
        
        # 加载频道脚本
        self._load_channel_script()
        
        # 创建服务器socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(128)
        
        self.running = True
        logger.info(f"Channel server started on {self.host}:{self.port}")
        
        # 启动接受连接线程
        accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        accept_thread.start()
    
    def stop(self):
        """停止频道服务器"""
        self.running = False
        
        # 关闭所有会话
        with self._lock:
            for session in self.sessions.values():
                try:
                    session.conn.close()
                except Exception:
                    pass
            self.sessions.clear()
        
        # 关闭服务器socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None
        
        logger.info("Channel server stopped")
    
    def add_channel(self, channel: ChannelInfo):
        """添加频道"""
        with self._lock:
            self.channels.append(channel)
    
    def remove_channel(self, channel_id: int):
        """移除频道"""
        with self._lock:
            self.channels = [c for c in self.channels if c.id != channel_id]
    
    def update_channel_users(self, channel_id: int, current_users: int):
        """更新频道当前人数"""
        with self._lock:
            for channel in self.channels:
                if channel.id == channel_id:
                    channel.current_users = current_users
                    break
    
    def _accept_loop(self):
        """接受连接循环"""
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                conn.settimeout(30)  # 30秒超时
                
                # 创建会话
                session_id = self._next_session_id()
                session = ChannelSession(
                    conn=conn,
                    addr=addr,
                    session_id=session_id,
                )
                
                with self._lock:
                    self.sessions[session_id] = session
                
                logger.info(f"Channel connection accepted: {addr} (session={session_id})")
                
                # 启动会话处理线程
                session_thread = threading.Thread(
                    target=self._handle_session,
                    args=(session,),
                    daemon=True,
                )
                session_thread.start()
                
            except socket.error as e:
                if self.running:
                    logger.error(f"Accept error: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected accept error: {e}")
    
    def _handle_session(self, session: ChannelSession):
        """处理会话"""
        try:
            # 握手阶段
            self._handle_handshake(session)
            
            # 主循环
            while session.connected and self.running:
                try:
                    # 检查是否是旧版请求
                    if not self._handle_legacy_request(session):
                        # 读取标准频道数据包
                        packet = self._read_channel_packet(session)
                        if packet:
                            self._handle_channel_packet(session, packet)
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Session error: {e}")
                    break
        except Exception as e:
            logger.error(f"Session handling error: {e}")
        finally:
            # 清理会话
            self._cleanup_session(session)
    
    def _handle_handshake(self, session: ChannelSession):
        """处理握手阶段"""
        try:
            # 读取头部（peek）
            header = self._peek_bytes(session.conn, LegacyChannelHeaderSize)
            if not header:
                return
            
            # 检查是否是DOF登录前缀
            if is_dof_login_preface_prefix(header):
                # 读取完整的DOF登录前缀
                raw = self._read_bytes(session.conn, DofLoginPrefaceSize)
                if raw:
                    logger.debug(f"Received DOF login preface from {session.addr}")
                    
                    # 发送DOF登录确认
                    ack = build_dof_login_ack(self.aes_key)
                    self._send_bytes(session.conn, ack)
                    logger.debug(f"Sent DOF login ack to {session.addr}")
        except Exception as e:
            logger.error(f"Handshake error: {e}")
    
    def _handle_legacy_request(self, session: ChannelSession) -> bool:
        """
        处理旧版频道请求
        
        Returns:
            是否处理了旧版请求
        """
        try:
            # 读取头部（peek）
            header = self._peek_bytes(session.conn, LegacyChannelHeaderSize)
            if not header:
                return False
            
            # 检查是否是DOF频道探测
            if is_dof_channel_probe_prefix(header):
                raw = self._read_bytes(session.conn, LegacyChannelHeaderSize)
                if raw:
                    logger.debug(f"Received DOF channel probe from {session.addr}")
                    self._send_legacy_script(session)
                return True
            
            # 检查是否是DOF询问频道
            if is_dof_ask_channel_prefix(header):
                raw = self._read_bytes(session.conn, DofAskChannelSize)
                if raw:
                    logger.debug(f"Received DOF ask channel from {session.addr}")
                    
                    bootstrap = session.script_sent
                    body = self._build_channel_info_body(raw[4:], bootstrap)
                    
                    packet = build_legacy_channel_packet(LegacyMsg.LegacyMsgChannelInfo, body)
                    self._send_bytes(session.conn, packet)
                    
                    if bootstrap:
                        session.close_after_bootstrap = True
                return True
            
            return False
        except Exception as e:
            logger.error(f"Legacy request error: {e}")
            return False
    
    def _read_channel_packet(self, session: ChannelSession) -> Optional[ChannelPacket]:
        """读取频道数据包"""
        try:
            # 读取头部
            header_data = self._read_bytes(session.conn, ChannelHeaderSize)
            if not header_data or len(header_data) < ChannelHeaderSize:
                return None
            
            # 检查是否是混合旧版包
            if header_data[0] != DefaultChannelClassification:
                # 尝试解析为混合旧版包
                packet = self._try_parse_mixed_legacy(session, header_data)
                if packet:
                    return packet
            
            # 读取body长度
            length = int.from_bytes(header_data[3:7], 'little')
            if length < ChannelHeaderSize:
                logger.warning(f"Invalid packet length: {length}")
                return None
            
            # 读取剩余数据
            remaining = length - ChannelHeaderSize
            body_data = b""
            if remaining > 0:
                body_data = self._read_bytes(session.conn, remaining)
                if not body_data or len(body_data) < remaining:
                    return None
            
            # 组合完整数据包
            full_packet = header_data + body_data
            
            # 解析（不校验校验和，因为某些包的校验和可能不标准）
            try:
                packet = parse_channel_packet(full_packet, verify_checksum=False)
            except Exception:
                packet = parse_channel_packet_unchecked(full_packet)
            
            logger.debug(
                f"Received channel packet: msg_id=0x{packet.header.msg_id:04x}, "
                f"seq={packet.header.seq}, body_size={len(packet.body)}"
            )
            
            return packet
            
        except Exception as e:
            logger.error(f"Read channel packet error: {e}")
            return None
    
    def _try_parse_mixed_legacy(
        self, session: ChannelSession, header: bytes
    ) -> Optional[ChannelPacket]:
        """尝试解析混合旧版包"""
        try:
            if len(header) < 4:
                return None
            
            body_len = int.from_bytes(header[0:2], 'big')
            msg_id = int.from_bytes(header[2:4], 'little')
            
            # 检查是否是已知的混合旧版消息
            if msg_id not in (ChannelMsg.MsgCSConnect, ChannelMsg.MsgCSAskChannelInfoNew):
                return None
            
            total = 4 + body_len
            if total < ChannelHeaderSize:
                return None
            
            # 读取剩余数据
            remaining = total - ChannelHeaderSize
            body_data = b""
            if remaining > 0:
                body_data = self._read_bytes(session.conn, remaining)
                if not body_data or len(body_data) < remaining:
                    return None
            
            # 组合body
            body = header[4:] + body_data
            
            # 构造标准包
            seq = 1
            for b in body:
                if b != 0:
                    seq = b
                    break
            
            packet = ChannelPacket(
                header=ChannelHeader(
                    classification=DefaultChannelClassification,
                    msg_id=msg_id,
                    length=total,
                    seq=seq,
                ),
                body=body,
            )
            
            return packet
            
        except Exception as e:
            logger.error(f"Parse mixed legacy error: {e}")
            return None
    
    def _handle_channel_packet(self, session: ChannelSession, packet: ChannelPacket):
        """处理频道数据包"""
        msg_id = packet.header.msg_id
        
        try:
            if msg_id == ChannelMsg.MsgCSUpdateChannelInfo:
                self._handle_update_channel_info(session, packet)
            elif msg_id == ChannelMsg.MsgCSConnect:
                self._handle_connect(session, packet)
            elif msg_id == ChannelMsg.MsgCSCheckScript:
                self._handle_check_script(session, packet)
            elif msg_id == ChannelMsg.MsgCSGetScript:
                self._handle_get_script(session, packet)
            elif msg_id == ChannelMsg.MsgCSAskChannelInfoNew:
                self._handle_ask_channel_info_new(session, packet)
            else:
                logger.debug(f"Unhandled channel msg: 0x{msg_id:04x}")
        except Exception as e:
            logger.error(f"Handle channel packet error: {e}")
    
    def _handle_update_channel_info(self, session: ChannelSession, packet: ChannelPacket):
        """处理更新频道信息"""
        body = self._build_channel_update_body()
        self._send_channel_packet(session, ChannelMsg.MsgSCAskChannelInfo, body)
    
    def _handle_connect(self, session: ChannelSession, packet: ChannelPacket):
        """处理连接"""
        body = self._build_connect_body()
        self._send_channel_packet(session, ChannelMsg.MsgSCConnect, body)
    
    def _handle_check_script(self, session: ChannelSession, packet: ChannelPacket):
        """处理检查脚本"""
        body = self._build_script_version_body()
        self._send_channel_packet(session, ChannelMsg.MsgSCCheckScript, body)
    
    def _handle_get_script(self, session: ChannelSession, packet: ChannelPacket):
        """处理获取脚本"""
        self._send_channel_script(session)
    
    def _handle_ask_channel_info_new(self, session: ChannelSession, packet: ChannelPacket):
        """处理询问频道信息（新版）"""
        # 如果还没发送脚本，先发送
        if not session.script_sent:
            self._send_channel_script(session)
        
        body = self._build_channel_info_body(packet.body, True)
        self._send_channel_packet(session, ChannelMsg.MsgSCAskChannelInfo, body)
    
    def _send_channel_script(self, session: ChannelSession):
        """发送频道脚本"""
        body = self._build_script_body()
        if body:
            self._send_channel_packet(session, ChannelMsg.MsgSCGetScript, body)
            session.script_sent = True
    
    def _send_legacy_script(self, session: ChannelSession):
        """发送旧版脚本"""
        body = self._build_script_body()
        if body:
            packet = build_legacy_channel_packet(LegacyMsg.LegacyMsgDofScript, body)
            self._send_bytes(session.conn, packet)
            session.script_sent = True
    
    def _send_channel_packet(
        self, session: ChannelSession, msg_id: int, body: bytes
    ):
        """发送频道数据包"""
        try:
            packet = build_channel_packet(msg_id, body, session.seq)
            session.seq = (session.seq + 1) & 0xFFFF
            
            self._send_bytes(session.conn, packet)
            
            logger.debug(
                f"Sent channel packet: msg_id=0x{msg_id:04x}, "
                f"seq={session.seq - 1}, body_size={len(body)}"
            )
        except Exception as e:
            logger.error(f"Send channel packet error: {e}")
            session.connected = False
    
    def _build_connect_body(self) -> bytes:
        """构建连接响应body"""
        body = bytearray(36)
        key_bytes = self.aes_key.encode('utf-8')[:16]
        body[4:4+len(key_bytes)] = key_bytes
        return bytes(body)
    
    def _build_script_version_body(self) -> bytes:
        """构建脚本版本响应body"""
        raw = bytearray(20)
        version_bytes = self.script_version.encode('utf-8')[:16]
        raw[4:4+len(version_bytes)] = version_bytes
        return encrypt_channel_data(bytes(raw), self.aes_key, compress=False)
    
    def _build_script_body(self) -> Optional[bytes]:
        """构建脚本body"""
        if self._channel_script:
            return encrypt_channel_data(self._channel_script, self.aes_key, compress=True)
        return None
    
    def _build_channel_update_body(self) -> bytes:
        """构建频道更新body"""
        with self._lock:
            if not self.channels:
                return b""
            
            channel = self.channels[0]
            
            writer = bytearray()
            # server_count (4字节)
            writer.extend((0).to_bytes(4, 'little'))
            # server_ip (16字节固定ASCII)
            ip_bytes = self.server_ip.encode('ascii')[:16]
            writer.extend(ip_bytes + b'\x00' * (16 - len(ip_bytes)))
            # port (4字节)
            writer.extend(channel.port.to_bytes(4, 'little', signed=True))
            # max_users (4字节)
            writer.extend(channel.max_users.to_bytes(4, 'little', signed=True))
            # current_users (4字节)
            writer.extend(channel.current_users.to_bytes(4, 'little', signed=True))
            
            return bytes(writer)
    
    def _build_channel_info_body(self, request: bytes, bootstrap: bool) -> bytes:
        """构建频道信息body"""
        with self._lock:
            channels = list(self.channels)
        
        # 读取请求的频道组
        group = self._read_null_ascii(request, 0, 20)
        
        # 前缀
        writer = bytearray()
        # server_count (4字节)
        writer.extend((1).to_bytes(4, 'little'))
        # server_id (4字节)
        writer.extend((1).to_bytes(4, 'little'))
        # channel_count (4字节)
        writer.extend(len(channels).to_bytes(4, 'little'))
        
        # 频道条目
        for channel in channels:
            # channel_name (20字节固定ASCII，前缀#)
            name = f"#{channel.name}"
            name_bytes = name.encode('ascii')[:20]
            writer.extend(name_bytes + b'\x00' * (20 - len(name_bytes)))
            
            # max_users (4字节)
            writer.extend(channel.max_users.to_bytes(4, 'little', signed=True))
            # current_users (4字节)
            writer.extend(channel.current_users.to_bytes(4, 'little', signed=True))
            # server_ip (16字节固定ASCII)
            ip_bytes = self.server_ip.encode('ascii')[:16]
            writer.extend(ip_bytes + b'\x00' * (16 - len(ip_bytes)))
            # port (4字节)
            writer.extend(channel.port.to_bytes(4, 'little', signed=True))
        
        return encrypt_channel_data(bytes(writer), self.aes_key, compress=True)
    
    def _load_channel_script(self):
        """加载频道脚本"""
        if self.channel_info_file:
            try:
                with open(self.channel_info_file, 'rb') as f:
                    self._channel_script = f.read()
                logger.info(f"Loaded channel script from {self.channel_info_file}")
            except Exception as e:
                logger.error(f"Failed to load channel script: {e}")
    
    def _read_null_ascii(self, data: bytes, offset: int, size: int) -> str:
        """读取以null结尾的ASCII字符串"""
        if offset >= len(data) or size <= 0:
            return ""
        
        limit = min(offset + size, len(data))
        end = offset
        while end < limit and data[end] != 0:
            end += 1
        
        return data[offset:end].decode('ascii', errors='ignore').strip()
    
    def _next_session_id(self) -> str:
        """生成下一个会话ID"""
        self._session_counter += 1
        return f"channel-{self._session_counter}"
    
    def _peek_bytes(self, conn: socket.socket, size: int) -> Optional[bytes]:
        """窥视字节（不消费）"""
        try:
            data = conn.recv(size, socket.MSG_PEEK)
            return data if data else None
        except Exception:
            return None
    
    def _read_bytes(self, conn: socket.socket, size: int) -> Optional[bytes]:
        """读取指定字节数"""
        try:
            data = b""
            while len(data) < size:
                chunk = conn.recv(size - len(data))
                if not chunk:
                    break
                data += chunk
            return data if len(data) == size else None
        except Exception:
            return None
    
    def _send_bytes(self, conn: socket.socket, data: bytes):
        """发送字节"""
        try:
            conn.sendall(data)
        except Exception as e:
            logger.error(f"Send error: {e}")
            raise
    
    def _cleanup_session(self, session: ChannelSession):
        """清理会话"""
        session.connected = False
        
        try:
            session.conn.close()
        except Exception:
            pass
        
        with self._lock:
            if session.session_id in self.sessions:
                del self.sessions[session.session_id]
        
        logger.info(f"Channel connection closed: {session.addr} (session={session.session_id})")
