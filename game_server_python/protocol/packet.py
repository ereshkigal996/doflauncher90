"""
数据包模块
实现旧版 packet 协议的解析和封装
"""

import struct
import zlib
from typing import Optional, IO

from .frame import Frame, FrameCodecRaw


# 数据包常量
PacketMagic = 0x5047  # "GP"
PacketVersion = 1
PacketHeaderSize = 20
MaxPacketBodySize = 4 * 1024 * 1024

# 数据包标志
PacketFlagCompressed = 1 << 0
PacketFlagChecksum = 1 << 1


class PacketError(Exception):
    """数据包错误基类"""
    pass


class InvalidPacketMagic(PacketError):
    """无效的数据包魔数"""
    pass


class InvalidPacketVersion(PacketError):
    """无效的数据包版本"""
    pass


class PacketBodyTooLarge(PacketError):
    """数据包体过大"""
    pass


class PacketChecksumInvalid(PacketError):
    """数据包校验和无效"""
    pass


class Packet:
    """
    旧版 packet 协议的内存表示
    
    Attributes:
        packet_id: 包ID（int32）
        msg_id: 消息ID（uint32）
        compressed: 是否压缩
        body: 包体数据
    """
    
    def __init__(
        self,
        packet_id: int = 0,
        msg_id: int = 0,
        compressed: bool = False,
        body: bytes = b"",
    ):
        self.packet_id = packet_id
        self.msg_id = msg_id
        self.compressed = compressed
        self.body = body
    
    def __repr__(self) -> str:
        return (
            f"Packet(packet_id={self.packet_id}, msg_id={self.msg_id}, "
            f"compressed={self.compressed}, body_size={len(self.body)})"
        )


def _packet_id_from_wire(value: int) -> int:
    """从线格式转换packet_id（uint32 -> int32）"""
    if value >= 0x80000000:
        return value - 0x100000000
    return value


def _packet_id_to_wire(value: int) -> int:
    """转换packet_id到线格式（int32 -> uint32）"""
    if value < 0:
        return value + 0x100000000
    return value & 0xFFFFFFFF


def read_packet(reader: IO[bytes], max_body_size: int = 0) -> Packet:
    """
    从 reader 读取并校验一个 packet
    
    Args:
        reader: 二进制读取器
        max_body_size: 最大包体大小（0表示使用默认值）
        
    Returns:
        Packet对象
        
    Raises:
        InvalidPacketMagic: 魔数无效
        InvalidPacketVersion: 版本无效
        PacketBodyTooLarge: 包体过大
        PacketChecksumInvalid: 校验和无效
    """
    if max_body_size == 0:
        max_body_size = MaxPacketBodySize
    
    # 读取头部
    header = reader.read(PacketHeaderSize)
    if len(header) < PacketHeaderSize:
        raise InvalidPacketMagic(f"header too short: {len(header)}")
    
    # 验证魔数
    magic = struct.unpack_from('<H', header, 0)[0]
    if magic != PacketMagic:
        raise InvalidPacketMagic(f"invalid magic: 0x{magic:04x}")
    
    # 验证版本
    version = header[2]
    if version != PacketVersion:
        raise InvalidPacketVersion(f"invalid version: {version}")
    
    # 标志位
    flags = struct.unpack_from('<H', header, 4)[0]
    compressed = bool(flags & PacketFlagCompressed)
    has_checksum = bool(flags & PacketFlagChecksum)
    
    # PacketID 和 MsgID
    packet_id = _packet_id_from_wire(struct.unpack_from('<I', header, 6)[0])
    msg_id = struct.unpack_from('<I', header, 10)[0]
    
    # 包体大小
    body_size = struct.unpack_from('<I', header, 14)[0]
    if body_size > max_body_size:
        raise PacketBodyTooLarge(f"body too large: {body_size} > {max_body_size}")
    
    # 读取包体
    body = b""
    if body_size > 0:
        body = reader.read(body_size)
        if len(body) < body_size:
            raise InvalidPacketMagic("body truncated")
    
    # 验证校验和
    if has_checksum:
        checksum = struct.unpack_from('<I', header, 18)[0] if len(header) >= 22 else 0
        if zlib.crc32(body) != checksum:
            raise PacketChecksumInvalid(f"checksum mismatch")
    
    return Packet(
        packet_id=packet_id,
        msg_id=msg_id,
        compressed=compressed,
        body=body,
    )


def write_packet(writer: IO[bytes], packet: Packet) -> None:
    """
    把 packet 写入 writer
    
    Args:
        writer: 二进制写入器
        packet: Packet对象
    """
    flags = 0
    if packet.compressed:
        flags |= PacketFlagCompressed
    
    # 构建头部
    header = bytearray(PacketHeaderSize)
    struct.pack_into('<H', header, 0, PacketMagic)
    header[2] = PacketVersion
    header[3] = 0  # 保留
    struct.pack_into('<H', header, 4, flags)
    struct.pack_into('<I', header, 6, _packet_id_to_wire(packet.packet_id))
    struct.pack_into('<I', header, 10, packet.msg_id)
    struct.pack_into('<I', header, 14, len(packet.body))
    
    # 写入
    writer.write(bytes(header))
    if packet.body:
        writer.write(packet.body)


def packet_to_frame(packet: Packet, sequence: int = 0) -> Frame:
    """
    将旧版 packet 转换为 frame_v1
    
    Args:
        packet: Packet对象
        sequence: 序列号
        
    Returns:
        Frame对象
    """
    flags = 0
    if packet.compressed:
        flags |= 1  # FrameFlagCompressed
    
    return Frame(
        version=1,  # FrameVersion1
        flags=flags,
        codec=0,  # FrameCodecRaw
        packet_id=packet.packet_id,
        msg_id=packet.msg_id,
        sequence=sequence,
        body=packet.body,
    )


def frame_to_packet(frame: Frame) -> Packet:
    """
    将 frame_v1 转换为旧版 packet
    
    Args:
        frame: Frame对象
        
    Returns:
        Packet对象
    """
    return Packet(
        packet_id=frame.packet_id,
        msg_id=frame.msg_id,
        compressed=frame.is_compressed(),
        body=frame.body,
    )
