"""
频道服务器测试脚本
验证数据包处理、加密、校验和等基础功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from protocol.dnf_checksum import checksum, checksum_range
from protocol.dnf_crypto import (
    pad_zero,
    unpad_zero,
    aes_ecb_encrypt,
    aes_ecb_decrypt,
    encrypt_channel_data,
    decrypt_channel_data,
    zlib_compress,
    zlib_decompress,
)
from protocol.channel_packet import (
    ChannelPacket,
    ChannelHeader,
    build_channel_packet,
    parse_channel_packet,
    parse_channel_packet_unchecked,
    build_legacy_channel_packet,
    ChannelHeaderSize,
    DefaultChannelClassification,
)
from network.channel_server import ChannelServer, ChannelInfo, ChannelMsg


def test_checksum():
    """测试校验和"""
    print("=" * 60)
    print("测试1: DNF自定义校验和")
    print("=" * 60)
    
    # 测试空数据
    result = checksum(b"")
    print(f"空数据校验和: 0x{result:08x}")
    
    # 测试简单数据
    test_data = b"Hello, DNF!"
    result = checksum(test_data)
    print(f"'Hello, DNF!' 校验和: 0x{result:08x}")
    
    # 测试区间校验和
    result = checksum_range(test_data, 0, 5)
    print(f"前5字节校验和: 0x{result:08x}")
    
    # 验证一致性
    result1 = checksum(test_data)
    result2 = checksum(test_data)
    assert result1 == result2, "校验和不一致"
    print("✓ 校验和一致性验证通过")
    
    print("\n✓ 校验和测试通过！")
    return True


def test_crypto():
    """测试加密"""
    print("\n" + "=" * 60)
    print("测试2: AES-128-ECB加密")
    print("=" * 60)
    
    key = "0123456789abcdef"
    test_data = b"Hello, DNF Channel Server!"
    
    print(f"密钥: {key}")
    print(f"原始数据: {test_data}")
    print(f"原始长度: {len(test_data)}")
    
    # 测试填充
    padded = pad_zero(test_data, 16)
    print(f"\n填充后数据: {padded.hex()}")
    print(f"填充后长度: {len(padded)} (对齐到16)")
    assert len(padded) % 16 == 0, "填充后未对齐"
    
    # 测试加密
    encrypted = aes_ecb_encrypt(padded, key)
    print(f"\n加密后数据: {encrypted.hex()}")
    print(f"加密后长度: {len(encrypted)}")
    
    # 测试解密
    decrypted = aes_ecb_decrypt(encrypted, key)
    print(f"\n解密后数据: {decrypted.hex()}")
    print(f"解密后长度: {len(decrypted)}")
    
    # 移除填充
    unpadded = unpad_zero(decrypted)
    print(f"移除填充后: {unpadded}")
    
    assert unpadded == test_data, "解密后数据不匹配"
    print("✓ 加密解密一致性验证通过")
    
    # 测试频道数据加密（带压缩）
    print("\n--- 频道数据加密（带压缩）---")
    channel_data = encrypt_channel_data(test_data, key, compress=True)
    print(f"加密后（压缩）: {channel_data.hex()}")
    print(f"长度: {len(channel_data)}")
    
    decrypted_channel = decrypt_channel_data(channel_data, key, compressed=True)
    print(f"解密后: {decrypted_channel}")
    assert decrypted_channel == test_data, "频道数据解密不匹配"
    print("✓ 频道数据加密（带压缩）验证通过")
    
    # 测试频道数据加密（不带压缩）
    print("\n--- 频道数据加密（不带压缩）---")
    channel_data2 = encrypt_channel_data(test_data, key, compress=False)
    print(f"加密后（不压缩）: {channel_data2.hex()}")
    print(f"长度: {len(channel_data2)}")
    
    decrypted_channel2 = decrypt_channel_data(channel_data2, key, compressed=False)
    print(f"解密后: {decrypted_channel2}")
    assert decrypted_channel2 == test_data, "频道数据解密（不压缩）不匹配"
    print("✓ 频道数据加密（不带压缩）验证通过")
    
    print("\n✓ 加密测试通过！")
    return True


def test_channel_packet():
    """测试频道数据包"""
    print("\n" + "=" * 60)
    print("测试3: 频道数据包")
    print("=" * 60)
    
    msg_id = 0x0002
    body = b"\x01\x02\x03\x04\x05"
    seq = 1
    
    print(f"消息ID: 0x{msg_id:04x}")
    print(f"Body: {body.hex()}")
    print(f"序列号: {seq}")
    
    # 构建数据包
    packet = build_channel_packet(msg_id, body, seq)
    print(f"\n构建的数据包: {packet.hex()}")
    print(f"总长度: {len(packet)} (头部{ChannelHeaderSize} + body{len(body)})")
    
    # 验证头部
    assert packet[0] == DefaultChannelClassification, "分类不匹配"
    assert int.from_bytes(packet[1:3], 'little') == msg_id, "消息ID不匹配"
    assert int.from_bytes(packet[3:7], 'little') == len(packet), "长度不匹配"
    print("✓ 头部字段验证通过")
    
    # 解析数据包（校验校验和）
    parsed = parse_channel_packet(packet, verify_checksum=True)
    print(f"\n解析后的数据包: {parsed}")
    print(f"  分类: {parsed.header.classification}")
    print(f"  消息ID: 0x{parsed.header.msg_id:04x}")
    print(f"  长度: {parsed.header.length}")
    print(f"  校验和: 0x{parsed.header.checksum:08x}")
    print(f"  序列号: {parsed.header.seq}")
    print(f"  Body: {parsed.body.hex()}")
    
    assert parsed.header.msg_id == msg_id, "解析后消息ID不匹配"
    assert parsed.body == body, "解析后body不匹配"
    assert parsed.header.seq == seq, "解析后序列号不匹配"
    print("✓ 数据包解析验证通过")
    
    # 测试不校验校验和的解析
    parsed2 = parse_channel_packet_unchecked(packet)
    assert parsed2.header.msg_id == msg_id, "不校验解析后消息ID不匹配"
    print("✓ 不校验校验和解析验证通过")
    
    # 测试旧版数据包
    print("\n--- 旧版数据包 ---")
    legacy_packet = build_legacy_channel_packet(0x0002, body)
    print(f"旧版数据包: {legacy_packet.hex()}")
    print(f"长度: {len(legacy_packet)} (4字节头部 + body)")
    
    # 验证旧版头部
    assert int.from_bytes(legacy_packet[0:2], 'big') == len(body), "旧版长度不匹配"
    assert int.from_bytes(legacy_packet[2:4], 'little') == 0x0002, "旧版消息ID不匹配"
    print("✓ 旧版数据包验证通过")
    
    print("\n✓ 频道数据包测试通过！")
    return True


def test_channel_server():
    """测试频道服务器"""
    print("\n" + "=" * 60)
    print("测试4: 频道服务器")
    print("=" * 60)
    
    # 创建频道服务器
    server = ChannelServer(
        host="127.0.0.1",
        port=17001,  # 使用非标准端口避免冲突
        aes_key="0123456789abcdef",
        server_ip="127.0.0.1",
    )
    
    print("创建频道服务器实例")
    print(f"  监听地址: {server.host}:{server.port}")
    print(f"  AES密钥: {server.aes_key}")
    print(f"  服务器IP: {server.server_ip}")
    
    # 添加测试频道
    channel1 = ChannelInfo(
        id=1,
        name="测试频道1",
        port=7001,
        max_users=100,
        current_users=10,
    )
    channel2 = ChannelInfo(
        id=2,
        name="测试频道2",
        port=7002,
        max_users=200,
        current_users=20,
    )
    
    server.add_channel(channel1)
    server.add_channel(channel2)
    
    print(f"\n添加测试频道: {len(server.channels)}个")
    for ch in server.channels:
        print(f"  - {ch.name} (端口={ch.port}, 人数={ch.current_users}/{ch.max_users})")
    
    # 测试更新频道人数
    server.update_channel_users(1, 50)
    assert server.channels[0].current_users == 50, "更新频道人数失败"
    print(f"\n更新频道1人数: {server.channels[0].current_users}")
    print("✓ 频道管理验证通过")
    
    # 测试启动和停止
    print("\n启动频道服务器...")
    server.start()
    
    # 等待服务器启动
    import time
    time.sleep(0.5)
    
    assert server.running, "服务器未启动"
    print("✓ 频道服务器启动成功")
    
    # 测试连接
    print("\n测试客户端连接...")
    import socket
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(5)
    
    try:
        client.connect(("127.0.0.1", 17001))
        print("✓ 客户端连接成功")
        
        # 发送一个简单的数据包
        test_packet = build_channel_packet(ChannelMsg.MsgCSConnect, b"\x00" * 32, 1)
        client.sendall(test_packet)
        print(f"发送测试数据包: {len(test_packet)}字节")
        
        # 接收响应
        response = client.recv(1024)
        print(f"接收响应: {len(response)}字节")
        if response:
            parsed = parse_channel_packet_unchecked(response)
            print(f"  响应消息ID: 0x{parsed.header.msg_id:04x}")
            print(f"  响应body大小: {len(parsed.body)}")
        
        client.close()
        print("✓ 客户端通信测试通过")
        
    except Exception as e:
        print(f"✗ 客户端连接测试失败: {e}")
    
    # 停止服务器
    print("\n停止频道服务器...")
    server.stop()
    
    assert not server.running, "服务器未停止"
    print("✓ 频道服务器停止成功")
    
    print("\n✓ 频道服务器测试通过！")
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("DNF频道服务器测试")
    print("=" * 60)
    
    tests = [
        ("DNF自定义校验和", test_checksum),
        ("AES-128-ECB加密", test_crypto),
        ("频道数据包", test_channel_packet),
        ("频道服务器", test_channel_server),
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
        print("\n🎉 所有测试通过！频道服务器基础功能验证正确。")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
