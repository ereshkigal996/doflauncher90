"""
游戏服务器测试脚本
验证游戏服务器的基础功能
"""

import sys
import os
import time
import socket

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from network.game_server import (
    GameServer,
    GameChannel,
    GameSession,
    GameStreamPacket,
    GameStreamKind,
)
from protocol.channel_packet import build_channel_packet, parse_channel_packet_unchecked


def test_game_server():
    """测试游戏服务器"""
    print("=" * 60)
    print("测试: 游戏服务器基础功能")
    print("=" * 60)
    
    # 创建游戏服务器
    server = GameServer(
        host="127.0.0.1",
        aes_key="0123456789abcdef",
        server_ip="127.0.0.1",
    )
    
    print("创建游戏服务器实例")
    print(f"  监听地址: {server.host}")
    print(f"  AES密钥: {server.aes_key}")
    print(f"  服务器IP: {server.server_ip}")
    
    # 添加测试频道
    channel1 = GameChannel(
        id=1,
        name="测试频道1",
        port=17002,
        max_users=100,
        current_users=0,
        type="normal",
    )
    channel2 = GameChannel(
        id=2,
        name="测试频道2",
        port=17003,
        max_users=200,
        current_users=0,
        type="normal",
    )
    
    server.add_channel(channel1)
    server.add_channel(channel2)
    
    print(f"\n添加测试频道: {len(server.channels)}个")
    for ch in server.channels:
        print(f"  - {ch.name} (端口={ch.port}, 人数={ch.current_users}/{ch.max_users})")
    
    # 启动服务器
    print("\n启动游戏服务器...")
    server.start()
    
    time.sleep(0.5)
    
    assert server.running, "服务器未启动"
    assert len(server.server_sockets) == 2, "监听器数量不正确"
    print("✓ 游戏服务器启动成功")
    print(f"  监听器数量: {len(server.server_sockets)}")
    
    # 测试客户端连接
    print("\n测试客户端连接...")
    
    for i, channel in enumerate(server.channels):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5)
        
        try:
            client.connect(("127.0.0.1", channel.port))
            print(f"✓ 客户端连接频道{i+1}成功 (端口={channel.port})")
            
            # 等待服务器处理连接
            time.sleep(0.2)
            
            # 检查会话数量
            with server._lock:
                session_count = len(server.sessions)
            print(f"  当前会话数: {session_count}")
            
            # 发送测试数据包
            test_body = b"\x00" * 16
            test_packet = build_channel_packet(0x0001, test_body, 1)
            client.sendall(test_packet)
            print(f"  发送测试数据包: {len(test_packet)}字节")
            
            # 等待处理
            time.sleep(0.2)
            
            client.close()
            print(f"  客户端连接已关闭")
            
        except Exception as e:
            print(f"✗ 客户端连接频道{i+1}失败: {e}")
    
    # 等待会话清理
    time.sleep(0.5)
    
    # 停止服务器
    print("\n停止游戏服务器...")
    server.stop()
    
    assert not server.running, "服务器未停止"
    assert len(server.server_sockets) == 0, "监听器未关闭"
    print("✓ 游戏服务器停止成功")
    
    print("\n✓ 游戏服务器测试通过！")
    return True


def test_game_stream_split():
    """测试游戏流分割"""
    print("\n" + "=" * 60)
    print("测试: 游戏流数据包分割")
    print("=" * 60)
    
    server = GameServer()
    
    # 测试1: 单个upper包
    print("\n测试1: 单个upper包")
    upper_packet = build_channel_packet(0x0001, b"\x00" * 16, 1)
    packets, remaining = server._split_game_stream(upper_packet)
    print(f"  输入: {len(upper_packet)}字节")
    print(f"  分割出: {len(packets)}个数据包")
    print(f"  剩余: {len(remaining)}字节")
    assert len(packets) == 1, "应该分割出1个包"
    assert packets[0].kind == GameStreamKind.Upper, "应该是upper包"
    assert len(remaining) == 0, "不应该有剩余"
    print("  ✓ 测试通过")
    
    # 测试2: 多个连续upper包
    print("\n测试2: 多个连续upper包")
    packet1 = build_channel_packet(0x0001, b"\x01" * 10, 1)
    packet2 = build_channel_packet(0x0002, b"\x02" * 20, 2)
    packet3 = build_channel_packet(0x0003, b"\x03" * 30, 3)
    combined = packet1 + packet2 + packet3
    packets, remaining = server._split_game_stream(combined)
    print(f"  输入: {len(combined)}字节 (3个包)")
    print(f"  分割出: {len(packets)}个数据包")
    print(f"  剩余: {len(remaining)}字节")
    assert len(packets) == 3, "应该分割出3个包"
    assert len(remaining) == 0, "不应该有剩余"
    print("  ✓ 测试通过")
    
    # 测试3: 不完整的包
    print("\n测试3: 不完整的包")
    incomplete = upper_packet[:10]  # 只取前10字节
    packets, remaining = server._split_game_stream(incomplete)
    print(f"  输入: {len(incomplete)}字节 (不完整)")
    print(f"  分割出: {len(packets)}个数据包")
    print(f"  剩余: {len(remaining)}字节")
    assert len(packets) == 0, "不应该分割出包"
    assert len(remaining) == len(incomplete), "应该保留所有数据"
    print("  ✓ 测试通过")
    
    # 测试4: 完整包 + 不完整包
    print("\n测试4: 完整包 + 不完整包")
    partial = packet2[:15]  # 第二个包只取前15字节
    combined = packet1 + partial
    packets, remaining = server._split_game_stream(combined)
    print(f"  输入: {len(combined)}字节 (1完整+1不完整)")
    print(f"  分割出: {len(packets)}个数据包")
    print(f"  剩余: {len(remaining)}字节")
    assert len(packets) == 1, "应该分割出1个包"
    assert len(remaining) == len(partial), "应该保留不完整的包"
    print("  ✓ 测试通过")
    
    print("\n✓ 游戏流数据包分割测试通过！")
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("DNF游戏服务器测试")
    print("=" * 60)
    
    tests = [
        ("游戏服务器基础功能", test_game_server),
        ("游戏流数据包分割", test_game_stream_split),
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
        print("\n🎉 所有测试通过！游戏服务器基础功能验证正确。")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
