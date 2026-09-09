"""
DNF自定义校验和模块
使用多项式0x4DB89129的CRC32算法
"""

# 校验和多项式
CHECKSUM_POLYNOMIAL = 1303941417  # 0x4DB89129

# 预计算校验和表
_checksum_table = None


def _build_checksum_table() -> list:
    """
    构建CRC32校验和表
    
    使用多项式0x4DB89129，与原版服务端一致
    """
    table = [0] * 256
    bit_value = 1
    
    bit = 128
    while bit != 0:
        if bit_value & 1:
            bit_value = CHECKSUM_POLYNOMIAL ^ (bit_value >> 1)
        else:
            bit_value >>= 1
        
        for left in range(0, 256, bit << 1):
            for right in range(bit):
                table[left + bit + right] = table[left + right] ^ bit_value
        
        bit >>= 1
    
    return table


def _get_checksum_table() -> list:
    """获取校验和表（懒加载）"""
    global _checksum_table
    if _checksum_table is None:
        _checksum_table = _build_checksum_table()
    return _checksum_table


def checksum(data: bytes) -> int:
    """
    计算DNF校验和
    
    Args:
        data: 输入数据
        
    Returns:
        32位校验和
    """
    return checksum_range(data, 0, len(data))


def checksum_range(data: bytes, offset: int, count: int) -> int:
    """
    计算指定区间的DNF校验和
    
    Args:
        data: 输入数据
        offset: 起始偏移
        count: 计算长度
        
    Returns:
        32位校验和
        
    Raises:
        ValueError: 区间无效
    """
    if count < 0 or offset < 0 or offset > len(data) - count:
        raise ValueError(f"invalid checksum range: offset={offset}, count={count}, len={len(data)}")
    
    table = _get_checksum_table()
    crc = 0xFFFFFFFF
    
    for i in range(count):
        crc = table[(crc ^ data[offset + i]) & 0xFF] ^ (crc >> 8)
    
    return ~crc & 0xFFFFFFFF
