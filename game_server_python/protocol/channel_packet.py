"""
频道数据包模块
实现DNF频道服务器的13字节raw upper包格式
"""

import struct
from typing import Optional

from .dnf_checksum import checksum_range


# 常量
ChannelHeaderSize = 13
GameServerUpperHeaderSize = ChannelHeaderSize
GameServerUpperHeaderSize16 = 16
DefaultChannelClassification = 1

# 旧版频道协议常量
LegacyChannelHeaderSize = 4
DofLoginPrefaceSize = 32
DofAskChannelSize = 32


class ChannelPacketError(Exception):
    """频道数据包错误基类"""
    pass


class ChannelHeader:
    """
    频道数据包头部（13字节）
    
    格式：
    - 1字节: Classification（分类）
    - 2字节: MsgID（小端）
    - 4字节: Length（小端，总长度）
    - 4字节: Checksum（小端）
    - 2字节: Seq（小端）
    """
    
    def __init__(
        self,
        classification: int = DefaultChannelClassification,
        msg_id: int = 0,
        length: int = 0,
        checksum: int = 0,
        seq: int = 0,
    ):
        self.classification = classification
        self.msg_id = msg_id
        self.length = length
        self.checksum = checksum
        self.seq = seq
    
    def __repr__(self) -> str:
        return (
            f"ChannelHeader(class={self.classification}, msg_id=0x{self.msg_id:04x}, "
            f"len={self.length}, checksum=0x{self.checksum:08x}, seq={self.seq})"
        )


class ChannelPacket:
    """
    频道数据包
    
    包含头部和body
    """
    
    def __init__(self, header: Optional[ChannelHeader] = None, body: bytes = b""):
        self.header = header or ChannelHeader()
        self.body = body
    
    def __repr__(self) -> str:
        return f"ChannelPacket(header={self.header}, body_size={len(self.body)})"


def build_channel_packet(
    msg_id: int,
    body: bytes,
    seq: int,
    classification: int = DefaultChannelClassification,
) -> bytes:
    """
    构建频道数据包（13字节头部）
    
    Args:
        msg_id: 消息ID
        body: 包体数据
        seq: 序列号
        classification: 分类（默认1）
        
    Returns:
        完整的数据包字节
        
    Raises:
        ChannelPacketError: 数据包过大
    """
    if classification == 0:
        classification = DefaultChannelClassification
    
    total = ChannelHeaderSize + len(body)
    if total > 0xFFFFFFFF:
        raise ChannelPacketError(f"packet too large: {total}")
    
    packet = bytearray(total)
    packet[0] = classification & 0xFF
    struct.pack_into('<H', packet, 1, msg_id & 0xFFFF)
    struct.pack_into('<I', packet, 3, total & 0xFFFFFFFF)
    struct.pack_into('<H', packet, 11, seq & 0xFFFF)
    packet[ChannelHeaderSize:] = body
    
    # 计算校验和（从第11字节到末尾）
    checksum = checksum_range(bytes(packet), 11, total - 11)
    struct.pack_into('<I', packet, 7, checksum & 0xFFFFFFFF)
    
    return bytes(packet)


def build_game_server_upper_packet(
    msg_id: int,
    body: bytes,
    seq: int,
    classification: int = DefaultChannelClassification,
    header_size: int = GameServerUpperHeaderSize,
) -> bytes:
    """
    构建游戏服务器上行数据包
    
    Args:
        msg_id: 消息ID
        body: 包体数据
        seq: 序列号
        classification: 分类
        header_size: 头部大小（13或16）
        
    Returns:
        完整的数据包字节
        
    Raises:
        ChannelPacketError: 头部大小无效或数据包过大
    """
    if header_size not in (ChannelHeaderSize, GameServerUpperHeaderSize16):
        raise ChannelPacketError(f"invalid header size: {header_size}")
    
    if classification == 0:
        classification = DefaultChannelClassification
    
    total = header_size + len(body)
    if total > 0xFFFFFFFF:
        raise ChannelPacketError(f"packet too large: {total}")
    
    packet = bytearray(total)
    packet[0] = classification & 0xFF
    struct.pack_into('<H', packet, 1, msg_id & 0xFFFF)
    struct.pack_into('<I', packet, 3, total & 0xFFFFFFFF)
    struct.pack_into('<H', packet, 11, seq & 0xFFFF)
    packet[header_size:] = body
    
    # 计算校验和（从第11字节到末尾）
    checksum = checksum_range(bytes(packet), 11, total - 11)
    struct.pack_into('<I', packet, 7, checksum & 0xFFFFFFFF)
    
    return bytes(packet)


def parse_channel_packet(packet: bytes, verify_checksum: bool = True) -> ChannelPacket:
    """
    解析频道数据包
    
    Args:
        packet: 数据包字节
        verify_checksum: 是否校验校验和
        
    Returns:
        ChannelPacket对象
        
    Raises:
        ChannelPacketError: 数据包过短、长度不匹配或校验和无效
    """
    if len(packet) < ChannelHeaderSize:
        raise ChannelPacketError(f"packet too short: {len(packet)} < {ChannelHeaderSize}")
    
    header = ChannelHeader(
        classification=packet[0],
        msg_id=struct.unpack_from('<H', packet, 1)[0],
        length=struct.unpack_from('<I', packet, 3)[0],
        checksum=struct.unpack_from('<I', packet, 7)[0],
        seq=struct.unpack_from('<H', packet, 11)[0],
    )
    
    if header.length < ChannelHeaderSize or header.length != len(packet):
        raise ChannelPacketError(
            f"packet length mismatch: header={header.length}, actual={len(packet)}"
        )
    
    if verify_checksum:
        expected_checksum = checksum_range(packet, 11, len(packet) - 11)
        if expected_checksum != header.checksum:
            raise ChannelPacketError(
                f"checksum mismatch: expected=0x{expected_checksum:08x}, "
                f"actual=0x{header.checksum:08x}"
            )
    
    body = bytes(packet[ChannelHeaderSize:])
    
    return ChannelPacket(header=header, body=body)


def parse_channel_packet_unchecked(packet: bytes) -> ChannelPacket:
    """
    解析频道数据包（不校验校验和）
    
    Args:
        packet: 数据包字节
        
    Returns:
        ChannelPacket对象
    """
    return parse_channel_packet(packet, verify_checksum=False)


# 旧版频道协议辅助函数

def is_dof_login_preface_prefix(header: bytes) -> bool:
    """
    检查是否是DOF登录前缀
    
    Args:
        header: 头部数据（至少4字节）
        
    Returns:
        是否是DOF登录前缀
    """
    if len(header) < 4:
        return False
    # DOF登录前缀特征：前2字节是0x00 0x20（大端长度32），后2字节是特定msg_id
    return header[0] == 0x00 and header[1] == 0x20


def is_dof_channel_probe_prefix(header: bytes) -> bool:
    """
    检查是否是DOF频道探测前缀
    
    Args:
        header: 头部数据（至少4字节）
        
    Returns:
        是否是DOF频道探测前缀
    """
    if len(header) < 4:
        return False
    # DOF频道探测前缀特征
    return header[0] == 0x00 and header[1] == 0x04


def is_dof_ask_channel_prefix(header: bytes) -> bool:
    """
    检查是否是DOF询问频道前缀
    
    Args:
        header: 头部数据（至少4字节）
        
    Returns:
        是否是DOF询问频道前缀
    """
    if len(header) < 4:
        return False
    # DOF询问频道前缀特征
    return header[0] == 0x00 and header[1] == 0x20


def build_dof_login_ack(key: str) -> bytes:
    """
    构建DOF登录确认包
    
    Args:
        key: AES密钥
        
    Returns:
        确认包数据
    """
    ack = bytearray(32)
    # 前4字节：长度和msg_id
    ack[0] = 0x00
    ack[1] = 0x20
    ack[2] = 0x00
    ack[3] = 0x00
    # 后续：密钥（16字节）
    key_bytes = key.encode('utf-8')[:16]
    ack[4:4+len(key_bytes)] = key_bytes
    return bytes(ack)


def build_legacy_channel_packet(msg_id: int, body: bytes) -> bytes:
    """
    构建旧版频道数据包
    
    Args:
        msg_id: 消息ID
        body: 包体数据
        
    Returns:
        完整的数据包字节
    """
    total = 4 + len(body)
    packet = bytearray(total)
    # 前2字节：大端长度
    struct.pack_into('>H', packet, 0, len(body))
    # 后2字节：小端msg_id
    struct.pack_into('<H', packet, 2, msg_id & 0xFFFF)
    packet[4:] = body
    return bytes(packet)
