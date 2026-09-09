"""
协议层测试脚本
验证帧处理、加密、数据包解析的正确性
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from protocol.frame import (
    Frame,
    FrameMagic,
    FrameVersion1,
    FrameHeaderSizeV1,
    FrameFlagCompressed,
    FrameFlagChecksum,
    FrameCodecRaw,
    FrameCodecJSON,
    read_frame,
    write_frame,
    frame_to_bytes,
    frame_from_bytes,
)
from protocol.frame_crypto import (
    derive_frame_session_key,
    encrypt_frame,
    decrypt_frame,
    FrameReplayGuard,
    FrameSessionKeySize,
    FrameNonceSize,
)
from protocol.packet import (
    Packet,
    read_packet,
    write_packet,
    packet_to_frame,
    frame_to_packet,
)

import io
import json


def test_frame_basic():
    """测试基本帧处理"""
    print("=" * 60)
    print("测试1: 基本帧处理")
    print("=" * 60)
    
    # 创建一个帧
    original_frame = Frame(
        version=FrameVersion1,
        flags=0,
        codec=FrameCodecJSON,
        packet_id=1001,
        msg_id=2002,
        sequence=1,
        body=json.dumps({"test": "hello", "num": 123}).encode('utf-8'),
        metadata={"traceparent": "00-1234567890abcdef-1234567890abcdef-01"},
    )
    
    print(f"原始帧: {original_frame}")
    print(f"  魔数: 0x{FrameMagic:04x}")
    print(f"  版本: {original_frame.version}")
    print(f"  编解码器: {original_frame.codec}")
    print(f"  PacketID: {original_frame.packet_id}")
    print(f"  MsgID: {original_frame.msg_id}")
    print(f"  Sequence: {original_frame.sequence}")
    print(f"  Body大小: {len(original_frame.body)} 字节")
    print(f"  Metadata: {original_frame.metadata}")
    
    # 序列化为字节
    frame_bytes = frame_to_bytes(original_frame)
    print(f"\n序列化后大小: {len(frame_bytes)} 字节")
    print(f"  头部大小: {FrameHeaderSizeV1} 字节")
    print(f"  前4字节: {frame_bytes[:4].hex()}")
    
    # 从字节解析
    parsed_frame = frame_from_bytes(frame_bytes)
    print(f"\n解析后帧: {parsed_frame}")
    
    # 验证
    assert parsed_frame.version == original_frame.version
    assert parsed_frame.flags == original_frame.flags
    assert parsed_frame.codec == original_frame.codec
    assert parsed_frame.packet_id == original_frame.packet_id
    assert parsed_frame.msg_id == original_frame.msg_id
    assert parsed_frame.sequence == original_frame.sequence
    assert parsed_frame.body == original_frame.body
    assert parsed_frame.metadata == original_frame.metadata
    
    print("\n✓ 基本帧处理测试通过！")
    return True


def test_frame_checksum():
    """测试帧校验和"""
    print("\n" + "=" * 60)
    print("测试2: 帧校验和")
    print("=" * 60)
    
    # 创建带校验和的帧
    frame = Frame(
        version=FrameVersion1,
        flags=FrameFlagChecksum,
        codec=FrameCodecRaw,
        packet_id=100,
        msg_id=200,
        sequence=1,
        body=b"Hello, World! This is a test message for checksum.",
    )
    
    print(f"原始帧: {frame}")
    print(f"  标志位: 0x{frame.flags:04x} (包含校验和)")
    
    # 序列化
    frame_bytes = frame_to_bytes(frame)
    print(f"序列化后大小: {len(frame_bytes)} 字节")
    
    # 解析
    parsed_frame = frame_from_bytes(frame_bytes)
    print(f"解析后帧: {parsed_frame}")
    print(f"  校验和: 0x{parsed_frame.checksum:08x}")
    
    # 验证
    assert parsed_frame.has_checksum()
    assert parsed_frame.body == frame.body
    
    print("\n✓ 帧校验和测试通过！")
    return True


def test_frame_crypto():
    """测试帧加密和解密"""
    print("\n" + "=" * 60)
    print("测试3: 帧加密和解密")
    print("=" * 60)
    
    # 派生会话密钥
    master_secret = "test_master_secret_1234567890"
    session_id = "test_session_001"
    key = derive_frame_session_key(master_secret, session_id)
    
    print(f"主密钥: {master_secret}")
    print(f"会话ID: {session_id}")
    print(f"派生密钥: {key.hex()}")
    print(f"密钥长度: {len(key)} 字节 (期望 {FrameSessionKeySize})")
    
    assert len(key) == FrameSessionKeySize
    
    # 创建原始帧
    original_frame = Frame(
        version=FrameVersion1,
        flags=0,
        codec=FrameCodecJSON,
        packet_id=1001,
        msg_id=2002,
        sequence=1,
        body=json.dumps({"user": "test", "action": "login"}).encode('utf-8'),
    )
    
    print(f"\n原始帧: {original_frame}")
    print(f"  原始Body: {original_frame.body}")
    
    # 加密
    encrypted_frame = encrypt_frame(original_frame, key)
    print(f"\n加密后帧: {encrypted_frame}")
    print(f"  加密标志: {encrypted_frame.is_encrypted()}")
    print(f"  加密后Body大小: {len(encrypted_frame.body)} 字节")
    print(f"  Nonce (前12字节): {encrypted_frame.body[:FrameNonceSize].hex()}")
    
    assert encrypted_frame.is_encrypted()
    assert encrypted_frame.body != original_frame.body
    
    # 解密
    decrypted_frame = decrypt_frame(encrypted_frame, key)
    print(f"\n解密后帧: {decrypted_frame}")
    print(f"  解密后Body: {decrypted_frame.body}")
    
    assert not decrypted_frame.is_encrypted()
    assert decrypted_frame.body == original_frame.body
    
    print("\n✓ 帧加密和解密测试通过！")
    return True


def test_frame_replay_guard():
    """测试重放保护"""
    print("\n" + "=" * 60)
    print("测试4: 重放保护")
    print("=" * 60)
    
    # 创建重放保护器
    guard = FrameReplayGuard(max_entries=100)
    
    # 派生密钥
    key = derive_frame_session_key("test_secret", "test_session")
    
    # 创建并加密第一个帧
    frame1 = Frame(sequence=1, body=b"first message")
    encrypted1 = encrypt_frame(frame1, key)
    nonce1 = encrypted1.body[:FrameNonceSize]
    
    print(f"第一个帧 sequence=1")
    print(f"  Nonce: {nonce1.hex()}")
    
    # 第一次应该成功
    try:
        guard.seen(nonce1)
        print("  第一次记录: 成功")
    except Exception as e:
        print(f"  第一次记录: 失败 - {e}")
        return False
    
    # 第二次应该失败（重放）
    try:
        guard.seen(nonce1)
        print("  第二次记录: 失败（应该抛出异常）")
        return False
    except Exception as e:
        print(f"  第二次记录: 成功检测到重放 - {type(e).__name__}")
    
    # 创建第二个不同的帧
    frame2 = Frame(sequence=2, body=b"second message")
    encrypted2 = encrypt_frame(frame2, key)
    nonce2 = encrypted2.body[:FrameNonceSize]
    
    print(f"\n第二个帧 sequence=2")
    print(f"  Nonce: {nonce2.hex()}")
    
    # 应该成功
    try:
        guard.seen(nonce2)
        print("  记录: 成功")
    except Exception as e:
        print(f"  记录: 失败 - {e}")
        return False
    
    print("\n✓ 重放保护测试通过！")
    return True


def test_packet():
    """测试数据包处理"""
    print("\n" + "=" * 60)
    print("测试5: 数据包处理")
    print("=" * 60)
    
    # 创建数据包
    original_packet = Packet(
        packet_id=1001,
        msg_id=2002,
        compressed=False,
        body=b"Test packet body",
    )
    
    print(f"原始数据包: {original_packet}")
    
    # 序列化为字节
    buf = io.BytesIO()
    write_packet(buf, original_packet)
    packet_bytes = buf.getvalue()
    print(f"序列化后大小: {len(packet_bytes)} 字节")
    
    # 解析
    buf.seek(0)
    parsed_packet = read_packet(buf)
    print(f"解析后数据包: {parsed_packet}")
    
    # 验证
    assert parsed_packet.packet_id == original_packet.packet_id
    assert parsed_packet.msg_id == original_packet.msg_id
    assert parsed_packet.compressed == original_packet.compressed
    assert parsed_packet.body == original_packet.body
    
    # 测试 packet <-> frame 转换
    print(f"\nPacket -> Frame 转换:")
    frame = packet_to_frame(original_packet, sequence=42)
    print(f"  Frame: {frame}")
    print(f"  Sequence: {frame.sequence}")
    
    print(f"\nFrame -> Packet 转换:")
    packet = frame_to_packet(frame)
    print(f"  Packet: {packet}")
    
    assert packet.packet_id == original_packet.packet_id
    assert packet.msg_id == original_packet.msg_id
    
    print("\n✓ 数据包处理测试通过！")
    return True


def test_negative_packet_id():
    """测试负数PacketID处理"""
    print("\n" + "=" * 60)
    print("测试6: 负数PacketID处理")
    print("=" * 60)
    
    # 测试负数
    test_ids = [-1, -100, -2147483648, 0, 100, 2147483647]
    
    for packet_id in test_ids:
        frame = Frame(packet_id=packet_id, body=b"test")
        frame_bytes = frame_to_bytes(frame)
        parsed_frame = frame_from_bytes(frame_bytes)
        
        status = "✓" if parsed_frame.packet_id == packet_id else "✗"
        print(f"  {status} PacketID={packet_id:>12} -> 解析后={parsed_frame.packet_id:>12}")
        
        assert parsed_frame.packet_id == packet_id
    
    print("\n✓ 负数PacketID处理测试通过！")
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("GameServer 协议层测试")
    print("=" * 60)
    
    tests = [
        ("基本帧处理", test_frame_basic),
        ("帧校验和", test_frame_checksum),
        ("帧加密和解密", test_frame_crypto),
        ("重放保护", test_frame_replay_guard),
        ("数据包处理", test_packet),
        ("负数PacketID处理", test_negative_packet_id),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result, None))
        except Exception as e:
            print(f"\n✗ 测试失败: {name}")
            print(f"  错误: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False, str(e)))
    
    # 汇总
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for name, result, error in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status}: {name}")
        if error:
            print(f"         错误: {error}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！协议层实现正确。")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
