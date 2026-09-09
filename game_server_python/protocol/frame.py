"""
帧协议模块
实现 gateway frame_v1 线协议的解析和封装
"""

import struct
import zlib
from typing import Optional, Dict, Tuple, IO


# 帧协议基础常量
FrameMagic = 0x5047  # 固定帧协议探测魔数："GP"
FrameVersion1 = 1
FrameHeaderSizeV1 = 32
MaxFrameBodySize = 4 * 1024 * 1024  # 4MB

# 标准帧 metadata 键名
FrameMetadataTraceParent = "traceparent"
FrameMetadataTraceState = "tracestate"
FrameMetadataBaggage = "baggage"
FrameMetadataIdempotencyKey = "idempotency-key"

# metadata 内部常量
_frameMetadataMagic = b"MD"
_frameMetadataVersion = 1
_frameMaxHeaderSize = 255

# 帧标志位
FrameFlagCompressed = 1 << 0  # 压缩
FrameFlagEncrypted = 1 << 1   # 加密
FrameFlagChecksum = 1 << 2    # 校验

# 帧 codec 标识
FrameCodecRaw = 0       # 原始字节
FrameCodecProtobuf = 1  # Protobuf
FrameCodecJSON = 2      # JSON


class FrameError(Exception):
    """帧协议错误基类"""
    pass


class InvalidFrameMagic(FrameError):
    """无效的帧魔数"""
    pass


class InvalidFrameVersion(FrameError):
    """无效的帧版本"""
    pass


class InvalidFrameHeader(FrameError):
    """无效的帧头部"""
    pass


class FrameBodyTooLarge(FrameError):
    """帧体过大"""
    pass


class FrameChecksumInvalid(FrameError):
    """帧校验和无效"""
    pass


class FrameMetadataInvalid(FrameError):
    """帧元数据无效"""
    pass


class Frame:
    """
    gateway frame_v1 线协议的内存表示
    
    Attributes:
        version: 版本号
        flags: 标志位（压缩、加密、校验）
        codec: 编解码器标识
        packet_id: 包ID（int32）
        msg_id: 消息ID（uint32）
        sequence: 序列号（uint64）
        checksum: 校验和（CRC32）
        body: 帧体数据
        metadata: 元数据键值对
    """
    
    def __init__(
        self,
        version: int = FrameVersion1,
        flags: int = 0,
        codec: int = FrameCodecRaw,
        packet_id: int = 0,
        msg_id: int = 0,
        sequence: int = 0,
        checksum: int = 0,
        body: bytes = b"",
        metadata: Optional[Dict[str, str]] = None,
    ):
        self.version = version
        self.flags = flags
        self.codec = codec
        self.packet_id = packet_id
        self.msg_id = msg_id
        self.sequence = sequence
        self.checksum = checksum
        self.body = body
        self.metadata = metadata or {}
    
    def __repr__(self) -> str:
        return (
            f"Frame(version={self.version}, flags=0x{self.flags:04x}, "
            f"codec={self.codec}, packet_id={self.packet_id}, msg_id={self.msg_id}, "
            f"sequence={self.sequence}, body_size={len(self.body)})"
        )
    
    def is_compressed(self) -> bool:
        """是否压缩"""
        return bool(self.flags & FrameFlagCompressed)
    
    def is_encrypted(self) -> bool:
        """是否加密"""
        return bool(self.flags & FrameFlagEncrypted)
    
    def has_checksum(self) -> bool:
        """是否有校验和"""
        return bool(self.flags & FrameFlagChecksum)


def _norm_max_frame_body(max_body_size: int) -> int:
    """规范化最大帧体大小"""
    if max_body_size == 0:
        return MaxFrameBodySize
    return max_body_size


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


def _encode_frame_meta(metadata: Dict[str, str]) -> bytes:
    """
    编码帧元数据
    
    格式：
    - 2字节: 魔数 "MD"
    - 1字节: 版本
    - 1字节: 条目数
    - 每个条目:
      - 1字节: key长度
      - 1字节: value长度
      - N字节: key
      - M字节: value
    """
    if not metadata:
        return b""
    
    # 规范化并过滤
    normalized = {}
    for key, value in metadata.items():
        key = key.strip().lower()
        value = value.strip()
        if key and value:
            normalized[key] = value
    
    if not normalized:
        return b""
    
    if len(normalized) > 255:
        raise FrameMetadataInvalid(f"metadata entries too large: {len(normalized)}")
    
    # 按key排序
    keys = sorted(normalized.keys())
    
    out = bytearray()
    out.extend(_frameMetadataMagic)
    out.append(_frameMetadataVersion)
    out.append(len(keys))
    
    for key in keys:
        value = normalized[key]
        if len(key) > 255 or len(value) > 255:
            raise FrameMetadataInvalid(f"metadata key/value too large: {key}")
        out.append(len(key))
        out.append(len(value))
        out.extend(key.encode('utf-8'))
        out.extend(value.encode('utf-8'))
        
        if FrameHeaderSizeV1 + len(out) > _frameMaxHeaderSize:
            raise FrameMetadataInvalid(f"header size too large: {FrameHeaderSizeV1 + len(out)}")
    
    return bytes(out)


def _decode_frame_meta(extra: bytes) -> Dict[str, str]:
    """
    解码帧元数据
    """
    if not extra:
        return {}
    
    if len(extra) < 4 or extra[:2] != _frameMetadataMagic:
        raise FrameMetadataInvalid("invalid metadata magic")
    
    if extra[2] != _frameMetadataVersion:
        raise FrameMetadataInvalid(f"invalid metadata version: {extra[2]}")
    
    count = extra[3]
    pos = 4
    out = {}
    
    for _ in range(count):
        if pos + 2 > len(extra):
            raise FrameMetadataInvalid("metadata truncated")
        
        key_len = extra[pos]
        value_len = extra[pos + 1]
        pos += 2
        
        if key_len == 0 or value_len == 0 or pos + key_len + value_len > len(extra):
            raise FrameMetadataInvalid("metadata entry truncated")
        
        key = extra[pos:pos + key_len].decode('utf-8').strip().lower()
        pos += key_len
        value = extra[pos:pos + value_len].decode('utf-8').strip()
        pos += value_len
        
        if key and value:
            out[key] = value
    
    if pos != len(extra):
        raise FrameMetadataInvalid("metadata trailing bytes")
    
    return out


def read_frame(reader: IO[bytes], max_body_size: int = 0) -> Frame:
    """
    从 reader 读取并校验一个 frame_v1 帧
    
    Args:
        reader: 二进制读取器
        max_body_size: 最大帧体大小（0表示使用默认值）
        
    Returns:
        Frame对象
        
    Raises:
        InvalidFrameMagic: 魔数无效
        InvalidFrameVersion: 版本无效
        InvalidFrameHeader: 头部无效
        FrameBodyTooLarge: 帧体过大
        FrameChecksumInvalid: 校验和无效
        FrameMetadataInvalid: 元数据无效
    """
    max_body_size = _norm_max_frame_body(max_body_size)
    
    # 读取固定头部
    header = reader.read(FrameHeaderSizeV1)
    if len(header) < FrameHeaderSizeV1:
        raise InvalidFrameHeader(f"header too short: {len(header)}")
    
    # 验证魔数
    magic = struct.unpack_from('<H', header, 0)[0]
    if magic != FrameMagic:
        raise InvalidFrameMagic(f"invalid magic: 0x{magic:04x}")
    
    # 验证版本
    version = header[2]
    if version != FrameVersion1:
        raise InvalidFrameVersion(f"invalid version: {version}")
    
    # 头部大小
    header_size = header[3]
    if header_size < FrameHeaderSizeV1:
        raise InvalidFrameHeader(f"header size too small: {header_size}")
    
    # 读取元数据头部
    metadata_header = b""
    if header_size > FrameHeaderSizeV1:
        metadata_header = reader.read(header_size - FrameHeaderSizeV1)
        if len(metadata_header) < header_size - FrameHeaderSizeV1:
            raise InvalidFrameHeader("metadata header truncated")
    
    # 解码元数据
    metadata = _decode_frame_meta(metadata_header)
    
    # 读取帧体大小
    body_size = struct.unpack_from('<I', header, 24)[0]
    if body_size > max_body_size:
        raise FrameBodyTooLarge(f"body too large: {body_size} > {max_body_size}")
    
    # 读取帧体
    body = b""
    if body_size > 0:
        body = reader.read(body_size)
        if len(body) < body_size:
            raise InvalidFrameHeader("body truncated")
    
    # 解析头部字段
    flags = struct.unpack_from('<H', header, 4)[0]
    codec = struct.unpack_from('<H', header, 6)[0]
    packet_id = _packet_id_from_wire(struct.unpack_from('<I', header, 8)[0])
    msg_id = struct.unpack_from('<I', header, 12)[0]
    sequence = struct.unpack_from('<Q', header, 16)[0]
    checksum = struct.unpack_from('<I', header, 28)[0]
    
    frame = Frame(
        version=version,
        flags=flags,
        codec=codec,
        packet_id=packet_id,
        msg_id=msg_id,
        sequence=sequence,
        checksum=checksum,
        body=body,
        metadata=metadata,
    )
    
    # 验证校验和
    if frame.has_checksum() and zlib.crc32(body) != checksum:
        raise FrameChecksumInvalid(f"checksum mismatch: {zlib.crc32(body):08x} != {checksum:08x}")
    
    return frame


def write_frame(writer: IO[bytes], frame: Frame) -> None:
    """
    把 frame_v1 帧写入 writer
    
    Args:
        writer: 二进制写入器
        frame: Frame对象
        
    Raises:
        InvalidFrameVersion: 版本无效
        FrameBodyTooLarge: 帧体过大
        FrameMetadataInvalid: 元数据无效
    """
    version = frame.version
    if version == 0:
        version = FrameVersion1
    if version != FrameVersion1:
        raise InvalidFrameVersion(f"invalid version: {version}")
    
    body_size = len(frame.body)
    if body_size > MaxFrameBodySize:
        raise FrameBodyTooLarge(f"body too large: {body_size}")
    
    # 编码元数据
    metadata_header = _encode_frame_meta(frame.metadata)
    header_size = FrameHeaderSizeV1 + len(metadata_header)
    if header_size > _frameMaxHeaderSize:
        raise FrameMetadataInvalid(f"header size too large: {header_size}")
    
    # 计算校验和
    checksum = frame.checksum
    if frame.has_checksum():
        checksum = zlib.crc32(frame.body)
    else:
        checksum = 0
    
    # 构建头部
    header = bytearray(FrameHeaderSizeV1)
    struct.pack_into('<H', header, 0, FrameMagic)
    header[2] = version
    header[3] = header_size
    struct.pack_into('<H', header, 4, frame.flags)
    struct.pack_into('<H', header, 6, frame.codec)
    struct.pack_into('<I', header, 8, _packet_id_to_wire(frame.packet_id))
    struct.pack_into('<I', header, 12, frame.msg_id)
    struct.pack_into('<Q', header, 16, frame.sequence)
    struct.pack_into('<I', header, 24, body_size)
    struct.pack_into('<I', header, 28, checksum)
    
    # 写入
    writer.write(bytes(header))
    if metadata_header:
        writer.write(metadata_header)
    if body_size > 0:
        writer.write(frame.body)


def frame_to_bytes(frame: Frame) -> bytes:
    """将帧序列化为字节"""
    import io
    buf = io.BytesIO()
    write_frame(buf, frame)
    return buf.getvalue()


def frame_from_bytes(data: bytes) -> Frame:
    """从字节解析帧"""
    import io
    return read_frame(io.BytesIO(data))
