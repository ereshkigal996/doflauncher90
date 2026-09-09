"""
帧加密模块
实现 frame_v1 的 AES-GCM 加密和解密，以及重放保护
"""

import os
import struct
import hashlib
from typing import Optional, Tuple, Set, List
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import HKDF
from Crypto.Hash import SHA256

from .frame import (
    Frame,
    FrameVersion1,
    FrameFlagEncrypted,
    InvalidFrameVersion,
    FrameError,
)


# 加密参数常量
FrameSessionKeySize = 32  # AES-256 密钥长度
FrameNonceSize = 12       # GCM nonce 长度


class FrameEncryptionError(FrameError):
    """帧加密错误基类"""
    pass


class FrameEncryptionKeyInvalid(FrameEncryptionError):
    """加密密钥无效"""
    pass


class FrameEncryptedPayloadInvalid(FrameEncryptionError):
    """加密负载无效"""
    pass


class FrameNonceReplay(FrameEncryptionError):
    """检测到 nonce 重放"""
    pass


class FrameReplayGuardFull(FrameEncryptionError):
    """重放保护器已满"""
    pass


def derive_frame_session_key(master_secret: str, session_id: str) -> bytes:
    """
    从主密钥和会话 ID 派生 frame 会话密钥
    
    使用 HKDF-SHA256 派生密钥
    
    Args:
        master_secret: 主密钥
        session_id: 会话ID
        
    Returns:
        32字节的会话密钥
        
    Raises:
        FrameEncryptionKeyInvalid: 主密钥或会话ID为空
    """
    if not master_secret or not session_id:
        raise FrameEncryptionKeyInvalid("master_secret or session_id is empty")
    
    # 使用 HKDF 派生密钥
    salt = session_id.encode('utf-8')
    info = b"longheng:frame-session-key:v1"
    
    key = HKDF(
        master=master_secret.encode('utf-8'),
        key_len=FrameSessionKeySize,
        salt=salt,
        hashmod=SHA256,
        context=info,
    )
    
    return key


def _frame_aad(frame: Frame) -> bytes:
    """
    构造帧的附加认证数据（AAD）
    
    AAD 包含帧头的关键字段，用于加密时的认证
    
    Args:
        frame: Frame对象
        
    Returns:
        AAD字节
    """
    # 21字节的固定AAD
    aad = bytearray(21)
    aad[0] = frame.version
    
    # Flags（清除加密标志，因为加密时还未设置）
    struct.pack_into('>H', aad, 1, frame.flags & ~FrameFlagEncrypted)
    
    # Codec
    struct.pack_into('>H', aad, 3, frame.codec)
    
    # PacketID
    struct.pack_into('>I', aad, 5, frame.packet_id & 0xFFFFFFFF)
    
    # MsgID
    struct.pack_into('>I', aad, 9, frame.msg_id)
    
    # Sequence
    struct.pack_into('>Q', aad, 13, frame.sequence)
    
    return bytes(aad)


def encrypt_frame(frame: Frame, key: bytes, random: Optional[bytes] = None) -> Frame:
    """
    加密 frame body，并把 nonce 放入密文前缀
    
    Args:
        frame: Frame对象
        key: 32字节的加密密钥
        random: 4字节的随机数（用于nonce的后4字节），如果为None则自动生成
        
    Returns:
        加密后的Frame对象
        
    Raises:
        InvalidFrameVersion: 版本无效
        FrameEncryptionKeyInvalid: 密钥无效
    """
    version = frame.version
    if version == 0:
        version = FrameVersion1
    if version != FrameVersion1:
        raise InvalidFrameVersion(f"invalid version: {version}")
    
    if len(key) != FrameSessionKeySize:
        raise FrameEncryptionKeyInvalid(f"invalid key size: {len(key)}")
    
    # 规范化version
    if frame.version == 0:
        frame.version = FrameVersion1
    
    # 构造 nonce：前8字节是大端 sequence，后4字节是随机
    nonce = bytearray(FrameNonceSize)
    struct.pack_into('>Q', nonce, 0, frame.sequence)
    
    if random is None:
        random = os.urandom(4)
    nonce[8:12] = random[:4]
    
    # 创建 AES-GCM cipher（使用自定义nonce）
    cipher = AES.new(key, AES.MODE_GCM, nonce=bytes(nonce))
    
    # 构造 AAD（使用规范化后的frame）
    aad = _frame_aad(frame)
    
    # 加密
    ciphertext, tag = cipher.encrypt_and_digest(frame.body)
    
    # 密文格式：nonce + ciphertext + tag
    encrypted_body = bytes(nonce) + ciphertext + tag
    
    # 创建加密后的帧
    encrypted_frame = Frame(
        version=version,
        flags=frame.flags | FrameFlagEncrypted,
        codec=frame.codec,
        packet_id=frame.packet_id,
        msg_id=frame.msg_id,
        sequence=frame.sequence,
        checksum=0,  # 加密时不使用校验和
        body=encrypted_body,
        metadata=frame.metadata.copy(),
    )
    
    return encrypted_frame


def decrypt_frame(
    frame: Frame,
    key: bytes,
    replay_guard: Optional['FrameReplayGuard'] = None,
) -> Frame:
    """
    解密 frame body 并执行可选 nonce 重放检查
    
    Args:
        frame: 加密的Frame对象
        key: 32字节的解密密钥
        replay_guard: 重放保护器（可选）
        
    Returns:
        解密后的Frame对象
        
    Raises:
        FrameEncryptionKeyInvalid: 密钥无效
        FrameEncryptedPayloadInvalid: 加密负载无效
        FrameNonceReplay: 检测到nonce重放
    """
    # 如果未加密，直接返回
    if not frame.is_encrypted():
        return frame
    
    if len(key) != FrameSessionKeySize:
        raise FrameEncryptionKeyInvalid(f"invalid key size: {len(key)}")
    
    # 检查密文长度
    if len(frame.body) < FrameNonceSize + 16:  # 16是GCM tag长度
        raise FrameEncryptedPayloadInvalid("encrypted payload too short")
    
    # 提取 nonce
    nonce = frame.body[:FrameNonceSize]
    
    # 提取密文和tag
    ciphertext = frame.body[FrameNonceSize:-16]
    tag = frame.body[-16:]
    
    # 构造 AAD
    aad = _frame_aad(frame)
    
    # 解密
    try:
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    except Exception as e:
        raise FrameEncryptedPayloadInvalid(f"decryption failed: {e}")
    
    # 重放检查
    if replay_guard is not None:
        replay_guard.seen(nonce)
    
    # 创建解密后的帧
    decrypted_frame = Frame(
        version=frame.version,
        flags=frame.flags & ~FrameFlagEncrypted,
        codec=frame.codec,
        packet_id=frame.packet_id,
        msg_id=frame.msg_id,
        sequence=frame.sequence,
        checksum=0,
        body=plaintext,
        metadata=frame.metadata.copy(),
    )
    
    return decrypted_frame


class FrameReplayGuard:
    """
    帧重放保护器
    
    在有界序号窗口内精确记录 nonce，防止同一会话内加密帧重放。
    
    nonce 前 8 字节是大端 frame sequence，后 4 字节是随机后缀。
    同一 sequence 可能因响应和 push 编号空间重叠而出现不同 nonce，
    因此窗口内按完整 nonce 去重；一旦 sequence 滑出窗口，
    其任何 nonce 都永久按重放拒绝。
    """
    
    def __init__(self, max_entries: int = 4096):
        """
        创建重放保护器
        
        Args:
            max_entries: 最大条目数（窗口大小）
        """
        if max_entries <= 0:
            max_entries = 4096
        
        self.max = max_entries
        self.initialized = False
        self.highest = 0
        self.total = 0
        self._seen_nonces: Set[bytes] = set()
        self.slots: List[Optional[dict]] = [None] * max_entries
    
    def _window(self) -> int:
        """获取窗口大小"""
        return self.max
    
    def seen(self, nonce: bytes) -> None:
        """
        记录 nonce；重复 nonce 或已滑出窗口的旧序号会返回重放错误
        
        Args:
            nonce: 12字节的nonce
            
        Raises:
            FrameEncryptedPayloadInvalid: nonce长度无效
            FrameNonceReplay: 检测到重放
            FrameReplayGuardFull: 保护器已满
        """
        if len(nonce) != FrameNonceSize:
            raise FrameEncryptedPayloadInvalid(f"invalid nonce size: {len(nonce)}")
        
        # 提取 sequence（前8字节，大端）
        sequence = struct.unpack('>Q', nonce[:8])[0]
        
        window = self._window()
        
        # 检查是否已滑出窗口
        if self.initialized and sequence <= self.highest and self.highest - sequence >= window:
            raise FrameNonceReplay(f"sequence {sequence} is outside window")
        
        # 初始化
        if not self.initialized:
            self.initialized = True
            self.highest = sequence
        elif sequence > self.highest:
            self._advance(sequence)
        
        # 检查是否已见过
        nonce_bytes = bytes(nonce)
        if nonce_bytes in self._seen_nonces:
            raise FrameNonceReplay(f"nonce replay detected")
        
        # 检查是否已满
        if self.total >= self.max:
            raise FrameReplayGuardFull("replay guard is full")
        
        # 记录到 slot
        slot_index = sequence % window
        slot = self.slots[slot_index]
        
        if slot is not None and slot['sequence'] != sequence:
            # 清除旧 slot
            self._clear_slot(slot_index)
            slot = None
        
        if slot is None:
            slot = {
                'sequence': sequence,
                'nonces': [],
            }
            self.slots[slot_index] = slot
        
        slot['nonces'].append(nonce_bytes)
        self._seen_nonces.add(nonce_bytes)
        self.total += 1
    
    def _advance(self, sequence: int) -> None:
        """推进窗口"""
        delta = sequence - self.highest
        window = self._window()
        
        if delta >= window:
            # 完全重置
            self.slots = [None] * self.max
            self._seen_nonces = set()
            self.total = 0
            self.highest = sequence
            return
        
        start = self.highest % window
        for step in range(1, delta + 1):
            self._clear_slot((start + step) % window)
        
        self.highest = sequence
    
    def _clear_slot(self, slot_index: int) -> None:
        """清除指定 slot"""
        slot = self.slots[slot_index]
        if slot is None:
            return
        
        for nonce in slot['nonces']:
            self._seen_nonces.discard(nonce)
            self.total -= 1
        
        if self.total < 0:
            self.total = 0
        
        self.slots[slot_index] = None
