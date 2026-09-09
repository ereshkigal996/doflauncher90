"""
游戏引导模块测试脚本
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.bootstrap import (
    GameBootstrap,
    PacketWriter,
    enc_notice_body,
    dec_notice_body,
    UpperMsg,
)
from game.character import MemoryCharacterRepository, CharacterManager


def test_packet_writer():
    """测试数据包写入器"""
    print("测试1: 数据包写入器")
    
    writer = PacketWriter()
    writer.write_byte(0x01)
    writer.write_uint16(0x1234)
    writer.write_uint32(0x12345678)
    writer.write_int32(-1)
    writer.write_ascii_dstr("test")
    writer.write_utf16_dstr("测试")
    
    data = writer.get_bytes()
    print(f"  写入数据长度: {len(data)}字节")
    print(f"  数据: {data.hex()}")
    
    # 验证
    assert data[0] == 0x01, "byte写入错误"
    assert data[1:3] == b'\x34\x12', "uint16写入错误"
    assert data[3:7] == b'\x78\x56\x34\x12', "uint32写入错误"
    assert data[7:11] == b'\xff\xff\xff\xff', "int32写入错误"
    
    print("  ✓ 数据包写入器测试通过")
    print()


def test_notice_encoding():
    """测试通知包体编解码"""
    print("测试2: 通知包体编解码")
    
    # 原始数据
    original = b'\x01\x02\x03\x04\x05\x06\x07\x08'
    
    # 编码
    encoded = enc_notice_body(original)
    print(f"  原始: {original.hex()}")
    print(f"  编码: {encoded.hex()}")
    
    # 解码
    decoded = dec_notice_body(encoded)
    print(f"  解码: {decoded.hex()}")
    
    # 验证
    assert decoded == original, "编解码不一致"
    
    print("  ✓ 通知包体编解码测试通过")
    print()


def test_channel_info_notice():
    """测试CHANNELINFO通知构建"""
    print("测试3: CHANNELINFO通知构建")
    
    bootstrap = GameBootstrap(server_ip="127.0.0.1")
    
    body = bootstrap.build_channel_info_notice(channel_id=1, channel_port=7002)
    print(f"  通知包体长度: {len(body)}字节")
    print(f"  通知包体: {body.hex()[:80]}...")
    
    # 验证编码后的数据
    decoded = dec_notice_body(body)
    print(f"  解码后长度: {len(decoded)}字节")
    print(f"  解码后首字节: 0x{decoded[0]:02x}")
    
    assert decoded[0] == 1, "通知包体首字节错误"
    
    print("  ✓ CHANNELINFO通知构建测试通过")
    print()


def test_login_success():
    """测试登录成功包构建"""
    print("测试4: 登录成功包构建")
    
    bootstrap = GameBootstrap(server_ip="127.0.0.1", game_outer_token=12345)
    
    body = bootstrap.build_login_success(
        channel_id=1,
        channel_port=7002,
        channel_type=0,
    )
    print(f"  登录成功包长度: {len(body)}字节")
    print(f"  登录成功包: {body.hex()}")
    
    # 验证
    assert body[0] == 1, "首字节错误"
    assert body[1] == 1, "第二字节错误"
    
    # 验证服务器IP
    # 格式: 1(固定) + 1(固定) + 1(频道类型) + 1(固定) + 4(token) + 1(IP长度) + IP内容
    ip_len = body[8]
    ip = body[9:9+ip_len].decode('ascii')
    print(f"  服务器IP: {ip}")
    assert ip == "127.0.0.1", "服务器IP错误"
    
    print("  ✓ 登录成功包构建测试通过")
    print()


def test_character_roster():
    """测试角色列表构建"""
    print("测试5: 角色列表构建")
    
    # 创建角色管理器
    repo = MemoryCharacterRepository()
    manager = CharacterManager(repo)
    
    # 创建测试角色
    char1 = manager.create_character(
        account_id="test_account",
        name="死亡左轮",
        job="gunner",
        slot=0,
        level=59,
    )
    char2 = manager.create_character(
        account_id="test_account",
        name="测试专用",
        job="swordman",
        slot=1,
        level=1,
    )
    
    bootstrap = GameBootstrap(character_manager=manager)
    
    # 空角色列表
    empty_body = bootstrap.build_empty_roster()
    print(f"  空角色列表长度: {len(empty_body)}字节")
    
    # 有角色的列表
    characters = manager.list_characters("test_account")
    roster_body = bootstrap.build_character_roster(characters)
    print(f"  角色列表长度: {len(roster_body)}字节")
    print(f"  角色数量: {roster_body[1]}")
    print(f"  槽位容量: {int.from_bytes(roster_body[2:4], 'little')}")
    
    assert roster_body[1] == 2, "角色数量错误"
    
    print("  ✓ 角色列表构建测试通过")
    print()


def test_bootstrap_flow():
    """测试完整引导流程"""
    print("测试6: 完整引导流程")
    
    # 创建角色管理器
    repo = MemoryCharacterRepository()
    manager = CharacterManager(repo)
    manager.create_character("test_account", "死亡左轮", "gunner", 0, 59)
    
    bootstrap = GameBootstrap(
        server_ip="127.0.0.1",
        character_manager=manager,
    )
    
    session_id = "test_session"
    
    # 步骤1: 发送初始CHANNELINFO通知
    notice = bootstrap.send_initial_notice(session_id, channel_id=1, channel_port=7002)
    print(f"  步骤1 - CHANNELINFO通知: {len(notice)}字节")
    
    state = bootstrap.get_state(session_id)
    assert state.channel_info_notice_sent, "CHANNELINFO通知未标记"
    
    # 步骤2: 处理CHANNELINFO请求
    responses = bootstrap.handle_packet(
        session_id=session_id,
        msg_id=UpperMsg.ChannelInfo,
        body=b'\x00\x00',
        channel_id=1,
        channel_port=7002,
        account_id="test_account",
    )
    print(f"  步骤2 - CHANNELINFO请求响应: {len(responses)}个包")
    assert len(responses) == 1, "应该返回1个响应"
    assert state.endpoint_success_sent, "登录成功未标记"
    
    # 步骤3: 处理GET_USERINFO请求
    responses = bootstrap.handle_packet(
        session_id=session_id,
        msg_id=UpperMsg.GetUserInfo,
        body=b'',
        channel_id=1,
        channel_port=7002,
        account_id="test_account",
    )
    print(f"  步骤3 - GET_USERINFO请求响应: {len(responses)}个包")
    assert len(responses) == 1, "应该返回1个响应"
    assert state.roster_requested, "角色列表未标记"
    
    # 步骤4: 处理SELECT_CHARACTER请求
    responses = bootstrap.handle_packet(
        session_id=session_id,
        msg_id=UpperMsg.SelectCharacter,
        body=b'\x00',
        channel_id=1,
        channel_port=7002,
        account_id="test_account",
    )
    print(f"  步骤4 - SELECT_CHARACTER请求响应: {len(responses)}个包")
    assert state.character_selected, "角色选择未标记"
    assert state.selected_character_id == 0, "选中角色ID错误"
    
    print("  ✓ 完整引导流程测试通过")
    print()


def main():
    """运行所有测试"""
    print("=" * 60)
    print("游戏引导模块测试")
    print("=" * 60)
    print()
    
    tests = [
        ("数据包写入器", test_packet_writer),
        ("通知包体编解码", test_notice_encoding),
        ("CHANNELINFO通知构建", test_channel_info_notice),
        ("登录成功包构建", test_login_success),
        ("角色列表构建", test_character_roster),
        ("完整引导流程", test_bootstrap_flow),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            test_func()
            results.append((name, True, None))
        except Exception as e:
            print(f"✗ 测试失败: {name}")
            print(f"  错误: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False, str(e)))
    
    # 汇总
    print("=" * 60)
    print("测试汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for name, result, error in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status}: {name}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！游戏引导模块基础功能验证正确。")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
