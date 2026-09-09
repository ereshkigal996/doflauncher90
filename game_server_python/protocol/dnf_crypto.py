"""
DNF加密模块
实现AES-128-ECB加密和zlib压缩，与原版服务端一致
"""

import zlib
from Crypto.Cipher import AES


# AES块大小
AES_BLOCK_SIZE = 16


class DnfCryptoError(Exception):
    """DNF加密错误基类"""
    pass


def pad_zero(data: bytes, align: int = AES_BLOCK_SIZE) -> bytes:
    """
    零填充到指定对齐大小
    
    Args:
        data: 输入数据
        align: 对齐大小
        
    Returns:
        填充后的数据
    """
    if align <= 0:
        return bytes(data)
    
    padding = (align - len(data) % align) % align
    if padding == 0:
        return bytes(data)
    
    return data + b'\x00' * padding


def unpad_zero(data: bytes) -> bytes:
    """
    移除零填充
    
    Args:
        data: 填充后的数据
        
    Returns:
        原始数据
    """
    return data.rstrip(b'\x00')


def aes_ecb_encrypt(data: bytes, key: str) -> bytes:
    """
    AES-128-ECB加密
    
    Args:
        data: 输入数据（必须是16字节对齐）
        key: 密钥字符串（取前16字节）
        
    Returns:
        加密后的数据
        
    Raises:
        DnfCryptoError: 数据不是16字节对齐
    """
    if len(data) % AES_BLOCK_SIZE != 0:
        raise DnfCryptoError(f"data is not block aligned: {len(data)} % {AES_BLOCK_SIZE} != 0")
    
    # 密钥取前16字节，不足补零
    key_bytes = key.encode('utf-8')[:AES_BLOCK_SIZE]
    if len(key_bytes) < AES_BLOCK_SIZE:
        key_bytes = key_bytes + b'\x00' * (AES_BLOCK_SIZE - len(key_bytes))
    
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    return cipher.encrypt(data)


def aes_ecb_decrypt(data: bytes, key: str) -> bytes:
    """
    AES-128-ECB解密
    
    Args:
        data: 加密数据（必须是16字节对齐）
        key: 密钥字符串（取前16字节）
        
    Returns:
        解密后的数据
        
    Raises:
        DnfCryptoError: 数据不是16字节对齐
    """
    if len(data) % AES_BLOCK_SIZE != 0:
        raise DnfCryptoError(f"data is not block aligned: {len(data)} % {AES_BLOCK_SIZE} != 0")
    
    # 密钥取前16字节，不足补零
    key_bytes = key.encode('utf-8')[:AES_BLOCK_SIZE]
    if len(key_bytes) < AES_BLOCK_SIZE:
        key_bytes = key_bytes + b'\x00' * (AES_BLOCK_SIZE - len(key_bytes))
    
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    return cipher.decrypt(data)


def zlib_compress(data: bytes) -> bytes:
    """
    zlib压缩
    
    Args:
        data: 输入数据
        
    Returns:
        压缩后的数据
    """
    return zlib.compress(data)


def zlib_decompress(data: bytes) -> bytes:
    """
    zlib解压
    
    Args:
        data: 压缩数据
        
    Returns:
        解压后的数据
    """
    return zlib.decompress(data)


def encrypt_channel_data(data: bytes, key: str, compress: bool = False) -> bytes:
    """
    加密频道数据（与原版服务端一致）
    
    流程：零填充 -> AES-128-ECB加密 -> 可选zlib压缩
    
    Args:
        data: 原始数据
        key: AES密钥
        compress: 是否压缩
        
    Returns:
        加密后的数据
    """
    # 零填充
    padded = pad_zero(data, AES_BLOCK_SIZE)
    
    # AES加密
    encrypted = aes_ecb_encrypt(padded, key)
    
    # 可选压缩
    if not compress:
        return encrypted
    
    return zlib_compress(encrypted)


def decrypt_channel_data(data: bytes, key: str, compressed: bool = False) -> bytes:
    """
    解密频道数据
    
    流程：可选zlib解压 -> AES-128-ECB解密 -> 移除零填充
    
    Args:
        data: 加密数据
        key: AES密钥
        compressed: 是否压缩过
        
    Returns:
        解密后的数据
    """
    # 可选解压
    if compressed:
        data = zlib_decompress(data)
    
    # AES解密
    decrypted = aes_ecb_decrypt(data, key)
    
    # 移除零填充
    return unpad_zero(decrypted)
