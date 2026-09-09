"""
DPROTO协议模块
实现DNF原生保护传输协议的信封格式和Provider接口

注意：具体的TerSafe加密算法是闭源的，需要通过外部Provider提供。
本模块只实现信封的解析和构建，以及Provider接口定义。
"""

import struct
from typing import Optional, List, Tuple, Protocol
from dataclasses import dataclass

from .channel_packet import (
    ChannelPacket,
    ChannelHeader,
    build_channel_packet,
    parse_channel_packet,
    parse_channel_packet_unchecked,
    ChannelHeaderSize,
    DefaultChannelClassification,
)


# DPROTO操作码
DprotoServerControlOpcode = 1466
DprotoServerEnvelopeOpcode = 1467
DprotoClientEnvelopeOpcode = 1517
DprotoCallbackOpcode = 1518


class DprotoError(Exception):
    """DPROTO错误基类"""
    pass


class DprotoEnvelopeOpcodeError(DprotoError):
    """DPROTO信封操作码无效"""
    pass


class DprotoEnvelopeBodyError(DprotoError):
    """DPROTO信封体无效"""
    pass


class DprotoProtectedSizeError(DprotoError):
    """DPROTO保护负载长度无效"""
    pass


@dataclass
class DprotoClientEnvelope:
    """
    DPROTO客户端信封（C2S）
    
    外层是标准的13字节ChannelHeader，
    body包含4字节protected_length + N字节protected payload
    """
    header: ChannelHeader
    protected: bytes
    raw: bytes


@dataclass
class DprotoDecodeResult:
    """
    DPROTO解码结果
    
    包含解密后的内部明文包和服务端需要发送的控制包
    """
    inner_packets: List[bytes]
    outbound_packets: List[bytes]


@dataclass
class DprotoEncodeResult:
    """
    DPROTO编码结果
    
    包含编码后的服务端数据包和是否受保护的标记
    """
    packet: bytes
    protected: bool


class DprotoSession(Protocol):
    """DPROTO会话接口"""
    
    def decode_client(self, data: bytes) -> DprotoDecodeResult:
        """解码客户端数据"""
        ...
    
    def encode_server(self, data: bytes) -> DprotoEncodeResult:
        """编码服务端数据"""
        ...
    
    def handle_client_control(self, opcode: int, data: bytes) -> List[bytes]:
        """处理客户端控制消息"""
        ...
    
    def close(self) -> None:
        """关闭会话"""
        ...


class DprotoProvider(Protocol):
    """DPROTO Provider接口"""
    
    def open_session(
        self,
        connection_id: str,
        remote_addr: str,
        local_addr: str,
        channel_id: int,
    ) -> DprotoSession:
        """打开一个DPROTO会话"""
        ...


def parse_dproto_client_envelope(
    raw: bytes,
    max_protected_bytes: int = 0,
) -> DprotoClientEnvelope:
    """
    解析DPROTO客户端信封
    
    Args:
        raw: 原始数据包
        max_protected_bytes: 最大保护负载大小（0表示不限制）
        
    Returns:
        DprotoClientEnvelope对象
        
    Raises:
        DprotoEnvelopeOpcodeError: 操作码无效
        DprotoEnvelopeBodyError: 信封体无效
        DprotoProtectedSizeError: 保护负载长度无效
    """
    # 解析外层ChannelPacket
    packet = parse_channel_packet(raw, verify_checksum=True)
    
    # 验证分类和操作码
    if (packet.header.classification != DefaultChannelClassification or
            packet.header.msg_id != DprotoClientEnvelopeOpcode):
        raise DprotoEnvelopeOpcodeError(
            f"invalid dproto envelope opcode: "
            f"class={packet.header.classification}, "
            f"msg_id={packet.header.msg_id}"
        )
    
    # 验证body长度
    if len(packet.body) < 4:
        raise DprotoEnvelopeBodyError(
            f"dproto envelope body too short: {len(packet.body)}"
        )
    
    # 读取protected_length
    protected_length = struct.unpack_from('<I', packet.body, 0)[0]
    
    # 验证protected_length
    if protected_length <= 0 or protected_length != len(packet.body) - 4:
        raise DprotoProtectedSizeError(
            f"invalid protected length: {protected_length}, "
            f"expected {len(packet.body) - 4}"
        )
    
    # 验证最大保护负载大小
    if max_protected_bytes > 0 and protected_length > max_protected_bytes:
        raise DprotoProtectedSizeError(
            f"protected payload too large: {protected_length} > {max_protected_bytes}"
        )
    
    # 提取protected payload
    protected = bytes(packet.body[4:])
    
    return DprotoClientEnvelope(
        header=packet.header,
        protected=protected,
        raw=bytes(raw),
    )


def build_dproto_client_envelope(protected: bytes, seq: int) -> bytes:
    """
    构建DPROTO客户端信封
    
    注意：生产环境的C2S信封由客户端构建，此函数主要用于测试。
    
    Args:
        protected: 保护负载
        seq: 序列号
        
    Returns:
        完整的信封数据包
        
    Raises:
        DprotoProtectedSizeError: 保护负载为空
    """
    if len(protected) == 0:
        raise DprotoProtectedSizeError("protected payload is empty")
    
    # 构建body：4字节length + protected
    body = bytearray(4 + len(protected))
    struct.pack_into('<I', body, 0, len(protected))
    body[4:] = protected
    
    # 构建外层ChannelPacket
    return build_channel_packet(
        DprotoClientEnvelopeOpcode,
        bytes(body),
        seq,
        DefaultChannelClassification,
    )


def is_dproto_client_envelope(data: bytes) -> bool:
    """
    检查数据是否是DPROTO客户端信封
    
    Args:
        data: 输入数据
        
    Returns:
        是否是DPROTO客户端信封
    """
    if len(data) < ChannelHeaderSize:
        return False
    
    # 检查classification和msg_id
    classification = data[0]
    msg_id = struct.unpack_from('<H', data, 1)[0]
    
    return (classification == DefaultChannelClassification and
            msg_id == DprotoClientEnvelopeOpcode)


def is_dproto_server_envelope(data: bytes) -> bool:
    """
    检查数据是否是DPROTO服务端信封
    
    Args:
        data: 输入数据
        
    Returns:
        是否是DPROTO服务端信封
    """
    if len(data) < ChannelHeaderSize:
        return False
    
    # 检查classification和msg_id
    classification = data[0]
    msg_id = struct.unpack_from('<H', data, 1)[0]
    
    return (classification == DefaultChannelClassification and
            msg_id == DprotoServerEnvelopeOpcode)


def is_dproto_packet(data: bytes) -> bool:
    """
    检查数据是否是DPROTO相关数据包
    
    Args:
        data: 输入数据
        
    Returns:
        是否是DPROTO相关数据包
    """
    if len(data) < ChannelHeaderSize:
        return False
    
    # 检查classification和msg_id
    classification = data[0]
    msg_id = struct.unpack_from('<H', data, 1)[0]
    
    if classification != DefaultChannelClassification:
        return False
    
    return msg_id in (
        DprotoServerControlOpcode,
        DprotoServerEnvelopeOpcode,
        DprotoClientEnvelopeOpcode,
        DprotoCallbackOpcode,
    )


class NullDprotoSession:
    """
    空DPROTO会话实现
    
    当没有可用的Provider时使用，不进行实际的加密/解密，
    只透传数据包。
    """
    
    def __init__(self, connection_id: str = ""):
        self.connection_id = connection_id
        self.closed = False
    
    def decode_client(self, data: bytes) -> DprotoDecodeResult:
        """解码客户端数据（空实现，返回空结果）"""
        return DprotoDecodeResult(
            inner_packets=[],
            outbound_packets=[],
        )
    
    def encode_server(self, data: bytes) -> DprotoEncodeResult:
        """编码服务端数据（空实现，直接返回原数据）"""
        return DprotoEncodeResult(
            packet=bytes(data),
            protected=False,
        )
    
    def handle_client_control(self, opcode: int, data: bytes) -> List[bytes]:
        """处理客户端控制消息（空实现）"""
        return []
    
    def close(self) -> None:
        """关闭会话"""
        self.closed = True


class NullDprotoProvider:
    """
    空DPROTO Provider实现
    
    当没有可用的加密服务时使用，创建NullDprotoSession。
    """
    
    def open_session(
        self,
        connection_id: str,
        remote_addr: str,
        local_addr: str,
        channel_id: int,
    ) -> NullDprotoSession:
        """打开一个空DPROTO会话"""
        return NullDprotoSession(connection_id)
