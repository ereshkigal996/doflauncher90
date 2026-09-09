"""
游戏引导模块
实现DNF游戏连接引导流程：CHANNELINFO通知 → 登录成功 → 角色列表 → 角色选择
"""

import struct
import time
import logging
from typing import Optional, List, Tuple
from dataclasses import dataclass, field

from protocol.channel_packet import (
    build_channel_packet,
    parse_channel_packet_unchecked,
    ChannelHeaderSize,
    DefaultChannelClassification,
)
from game.character import CharacterRecord, CharacterManager


# 日志
logger = logging.getLogger(__name__)


# 上层消息ID枚举
class UpperMsg:
    """上层消息ID"""
    # 游戏端点
    GameEndpoint = 0x0001
    
    # 频道信息
    ChannelInfo = 0x0002
    ChannelInfoUpdate = 0x0003
    
    # 脚本检查
    CheckScript = 0x0004
    GetScript = 0x0005
    
    # 角色相关
    CharacterRoster = 0x0008
    SelectCharacter = 0x0009
    CreateCharacter = 0x000A
    DeleteCharacter = 0x000B
    
    # 用户信息
    GetUserInfo = 0x0007
    
    # 客户端检查
    ClientCheck = 0x000C
    
    # 守护控制
    GuardControl = 0x000D
    
    # 游戏命令
    GameCmdNotice = 0x000E
    
    # 游戏类型
    GameTypeCharacterList = 0x000F


# 频道名称前缀
CHANNEL_NAME_PREFIX = "CH."


@dataclass
class GameBootstrapState:
    """游戏引导状态"""
    # 连接状态
    channel_info_notice_sent: bool = False
    endpoint_success_sent: bool = False
    roster_requested: bool = False
    
    # 角色选择状态
    selected_character_id: int = 0
    character_selected: bool = False
    
    # 场景状态
    scene_bootstrap_sent: bool = False
    town_entered: bool = False
    
    # 时间戳
    connect_time: float = 0.0
    last_activity_time: float = 0.0


class PacketWriter:
    """数据包写入器"""
    
    def __init__(self):
        self.data = bytearray()
    
    def write_byte(self, value: int) -> None:
        """写入1字节"""
        self.data.append(value & 0xFF)
    
    def write_uint16(self, value: int) -> None:
        """写入2字节无符号整数（小端）"""
        self.data.extend(struct.pack('<H', value & 0xFFFF))
    
    def write_uint32(self, value: int) -> None:
        """写入4字节无符号整数（小端）"""
        self.data.extend(struct.pack('<I', value & 0xFFFFFFFF))
    
    def write_int32(self, value: int) -> None:
        """写入4字节有符号整数（小端）"""
        self.data.extend(struct.pack('<i', value))
    
    def write_bytes(self, data: bytes) -> None:
        """写入字节数组"""
        self.data.extend(data)
    
    def write_zero(self, count: int) -> None:
        """写入指定数量的零字节"""
        self.data.extend(b'\x00' * count)
    
    def write_ascii_dstr(self, text: str) -> None:
        """写入ASCII动态字符串（1字节长度 + 内容）"""
        encoded = text.encode('ascii', errors='replace')
        self.write_byte(len(encoded))
        self.data.extend(encoded)
    
    def write_utf16_dstr(self, text: str) -> None:
        """写入UTF-16动态字符串（2字节长度 + 内容）"""
        encoded = text.encode('utf-16-le')
        self.write_uint16(len(encoded) // 2)
        self.data.extend(encoded)
    
    def get_bytes(self) -> bytes:
        """获取最终字节数组"""
        return bytes(self.data)


def enc_notice_body(body: bytes) -> bytes:
    """
    编码通知包体
    
    使用 RotateLeft8(b, 2) ^ 0xd6 编码
    """
    encoded = bytearray(len(body))
    for i, b in enumerate(body):
        # RotateLeft8(b, 2): 循环左移2位
        rotated = ((b << 2) | (b >> 6)) & 0xFF
        encoded[i] = rotated ^ 0xD6
    return bytes(encoded)


def dec_notice_body(body: bytes) -> bytes:
    """
    解码通知包体
    
    反向操作: (b ^ 0xd6) 循环右移2位
    """
    decoded = bytearray(len(body))
    for i, b in enumerate(body):
        xored = b ^ 0xD6
        # RotateRight8(xored, 2): 循环右移2位
        rotated = ((xored >> 2) | (xored << 6)) & 0xFF
        decoded[i] = rotated
    return bytes(decoded)


class GameBootstrap:
    """
    游戏引导处理器
    
    处理游戏连接引导流程：
    1. CHANNELINFO通知
    2. 登录成功
    3. 角色列表
    4. 角色选择
    """
    
    def __init__(
        self,
        server_ip: str = "127.0.0.1",
        game_outer_token: int = 0,
        character_manager: Optional[CharacterManager] = None,
    ):
        """
        初始化游戏引导处理器
        
        Args:
            server_ip: 服务器IP
            game_outer_token: 游戏外部令牌
            character_manager: 角色管理器
        """
        self.server_ip = server_ip
        self.game_outer_token = game_outer_token
        self.character_manager = character_manager
        
        # 会话状态（按会话ID存储）
        self._states: dict = {}
    
    def get_state(self, session_id: str) -> GameBootstrapState:
        """获取会话状态"""
        if session_id not in self._states:
            self._states[session_id] = GameBootstrapState(
                connect_time=time.time(),
                last_activity_time=time.time(),
            )
        return self._states[session_id]
    
    def remove_state(self, session_id: str) -> None:
        """移除会话状态"""
        if session_id in self._states:
            del self._states[session_id]
    
    def build_channel_info_notice(self, channel_id: int, channel_port: int) -> bytes:
        """
        构建CHANNELINFO通知包体
        
        Args:
            channel_id: 频道ID
            channel_port: 频道端口
            
        Returns:
            编码后的通知包体
        """
        writer = PacketWriter()
        
        # C# BuildInitialLoginNotice 格式
        writer.write_byte(1)  # 固定
        writer.write_ascii_dstr(f"{CHANNEL_NAME_PREFIX}{channel_id}")  # 频道名称
        writer.write_int32(0)  # 未知
        writer.write_int32(0)  # 未知
        writer.write_byte(0)  # 频道广告ID
        writer.write_byte(channel_id)  # 频道ID
        writer.write_byte(0)  # 未知
        writer.write_int32(int(time.time()))  # 时间戳
        writer.write_int32(1)  # 固定
        writer.write_ascii_dstr(self.server_ip)  # 服务器IP
        writer.write_int32(0)  # UDP端口1
        writer.write_int32(0)  # UDP端口2
        writer.write_byte(0)  # 未知
        writer.write_byte(0)  # 未知
        writer.write_int32(0)  # 命令计数
        writer.write_int32(0)  # 通知计数
        
        body = writer.get_bytes()
        
        # 编码通知包体
        return enc_notice_body(body)
    
    def build_login_success(self, channel_id: int, channel_port: int, channel_type: int = 0) -> bytes:
        """
        构建登录成功包体
        
        Args:
            channel_id: 频道ID
            channel_port: 频道端口
            channel_type: 频道类型
            
        Returns:
            登录成功包体
        """
        writer = PacketWriter()
        
        writer.write_byte(1)  # 固定
        writer.write_byte(1)  # 固定
        writer.write_byte(channel_type)  # 频道类型
        writer.write_byte(1)  # 固定
        writer.write_uint32(self.game_outer_token)  # 游戏外部令牌
        writer.write_ascii_dstr(self.server_ip)  # 服务器IP
        writer.write_int32(channel_port)  # 游戏端口
        writer.write_int32(0)  # 未知
        
        # 账号状态（24字节）
        account_state = bytearray(24)
        account_state[2] = 1  # useSecurityCard
        account_state[3] = 1  # alreadyAuthentificatedSecurityCard
        writer.write_bytes(bytes(account_state))
        
        return writer.get_bytes()
    
    def build_empty_roster(self, slot_capacity: int = 32) -> bytes:
        """
        构建空角色列表包体
        
        Args:
            slot_capacity: 槽位容量
            
        Returns:
            空角色列表包体
        """
        writer = PacketWriter()
        
        # 15字节头部
        writer.write_byte(1)  # 标记
        writer.write_byte(0)  # 角色数量
        writer.write_uint16(slot_capacity)  # 槽位容量
        writer.write_uint16(0)  # 选中页
        writer.write_uint16(0)  # 未知
        writer.write_uint16(0)  # 条目数量
        writer.write_uint16(0)  # 未知
        
        return writer.get_bytes()
    
    def build_character_roster(
        self,
        characters: List[CharacterRecord],
        slot_capacity: int = 32,
    ) -> bytes:
        """
        构建角色列表包体
        
        Args:
            characters: 角色列表
            slot_capacity: 槽位容量
            
        Returns:
            角色列表包体
        """
        if not characters:
            return self.build_empty_roster(slot_capacity)
        
        writer = PacketWriter()
        
        # 15字节头部
        writer.write_byte(1)  # 标记
        writer.write_byte(len(characters))  # 角色数量
        writer.write_uint16(slot_capacity)  # 槽位容量
        writer.write_uint16(0)  # 选中页
        writer.write_uint16(0)  # 未知
        writer.write_uint16(len(characters))  # 条目数量
        writer.write_uint16(0)  # 未知
        
        # 每个角色条目（简化版本）
        for char in characters:
            self._write_character_entry(writer, char)
        
        return writer.get_bytes()
    
    def _write_character_entry(self, writer: PacketWriter, char: CharacterRecord) -> None:
        """
        写入角色条目（简化版本）
        
        Args:
            writer: 数据包写入器
            char: 角色记录
        """
        # 角色条目格式非常复杂，这里使用简化版本
        # 实际格式需要根据客户端协议精确实现
        
        # 基础信息
        writer.write_byte(char.slot)  # 槽位
        writer.write_byte(0)  # 未知
        writer.write_uint16(char.level)  # 等级
        
        # 职业信息（简化）
        job_id = self._job_to_id(char.job)
        writer.write_uint16(job_id)  # 职业ID
        writer.write_uint16(0)  # 转职ID
        
        # 角色名称（UTF-16）
        writer.write_utf16_dstr(char.name)
        
        # 公会名称（空）
        writer.write_utf16_dstr("")
        
        # 装备摘要（简化，12个装备槽位）
        for _ in range(12):
            writer.write_uint32(0)  # 物品ID
            writer.write_byte(0)  # 强化等级
            writer.write_byte(0)  # 未知
        
        # 外观信息（简化）
        writer.write_uint32(0)  # 头发
        writer.write_uint32(0)  # 帽子
        writer.write_uint32(0)  # 脸
        writer.write_uint32(0)  # 皮肤
        
        # 属性信息（简化）
        writer.write_uint32(char.stats.get('hp', 1000))  # HP
        writer.write_uint32(char.stats.get('mp', 500))  # MP
        writer.write_uint16(char.stats.get('strength', 10))  # 力量
        writer.write_uint16(char.stats.get('intelligence', 10))  # 智力
        writer.write_uint16(char.stats.get('vitality', 10))  # 体力
        writer.write_uint16(char.stats.get('spirit', 10))  # 精神
        
        # 位置信息
        writer.write_uint32(char.location.town_id)  # 城镇ID
        writer.write_uint32(char.location.dungeon_id)  # 副本ID
        
        # 经验值
        writer.write_uint32(char.exp)  # 经验
        
        # 填充（简化版本，实际格式更复杂）
        writer.write_zero(64)
    
    def _job_to_id(self, job: str) -> int:
        """
        职业名称转ID
        
        Args:
            job: 职业名称
            
        Returns:
            职业ID
        """
        job_map = {
            'swordman': 0,      # 鬼剑士
            'fighter': 1,       # 格斗家
            'gunner': 2,        # 神枪手
            'mage': 3,          # 魔法师
            'priest': 4,        # 圣职者
            'thief': 5,         # 暗夜使者
            'knight': 6,        # 守护者
            'demonic_lancer': 7,  # 魔枪士
            'gun_blader': 8,    # 枪剑士
            'slayer': 0,        # 剑魂（鬼剑士转职）
            'berserker': 0,     # 狂战士（鬼剑士转职）
            'asura': 0,         # 阿修罗（鬼剑士转职）
            'devil_may_cry': 0,  # 鬼泣（鬼剑士转职）
        }
        return job_map.get(job.lower(), 0)
    
    def handle_channel_info_request(
        self,
        session_id: str,
        channel_id: int,
        channel_port: int,
    ) -> Optional[bytes]:
        """
        处理CHANNELINFO请求
        
        Args:
            session_id: 会话ID
            channel_id: 频道ID
            channel_port: 频道端口
            
        Returns:
            响应数据包（如果需要发送）
        """
        state = self.get_state(session_id)
        state.last_activity_time = time.time()
        
        # 如果已经发送过端点成功，不再响应
        if state.endpoint_success_sent:
            return None
        
        # 发送登录成功
        body = self.build_login_success(channel_id, channel_port)
        state.endpoint_success_sent = True
        
        logger.info(f"[{session_id}] 发送登录成功 (channel={channel_id}, port={channel_port})")
        
        return build_channel_packet(UpperMsg.GameEndpoint, body, 0)
    
    def handle_get_user_info(
        self,
        session_id: str,
        account_id: str,
    ) -> Optional[bytes]:
        """
        处理GET_USERINFO请求
        
        Args:
            session_id: 会话ID
            account_id: 账号ID
            
        Returns:
            角色列表数据包
        """
        state = self.get_state(session_id)
        state.last_activity_time = time.time()
        state.roster_requested = True
        
        # 获取角色列表
        characters = []
        if self.character_manager:
            characters = self.character_manager.list_characters(account_id)
        
        # 构建角色列表
        body = self.build_character_roster(characters)
        
        logger.info(f"[{session_id}] 发送角色列表 (account={account_id}, count={len(characters)})")
        
        return build_channel_packet(UpperMsg.CharacterRoster, body, 0)
    
    def handle_select_character(
        self,
        session_id: str,
        character_slot: int,
        account_id: str,
    ) -> Optional[bytes]:
        """
        处理SELECT_CHARACTER请求
        
        Args:
            session_id: 会话ID
            character_slot: 角色槽位
            account_id: 账号ID
            
        Returns:
            响应数据包
        """
        state = self.get_state(session_id)
        state.last_activity_time = time.time()
        state.selected_character_id = character_slot
        state.character_selected = True
        
        logger.info(f"[{session_id}] 角色选择 (slot={character_slot}, account={account_id})")
        
        # 角色选择后需要发送大量场景初始化数据包
        # 这里先返回一个简单的确认
        # 实际实现需要发送完整的场景引导
        
        return None
    
    def handle_packet(
        self,
        session_id: str,
        msg_id: int,
        body: bytes,
        channel_id: int,
        channel_port: int,
        account_id: str = "",
    ) -> List[bytes]:
        """
        处理游戏数据包
        
        Args:
            session_id: 会话ID
            msg_id: 消息ID
            body: 消息体
            channel_id: 频道ID
            channel_port: 频道端口
            account_id: 账号ID
            
        Returns:
            响应数据包列表
        """
        responses = []
        
        try:
            if msg_id == UpperMsg.ChannelInfo:
                # CHANNELINFO请求
                response = self.handle_channel_info_request(
                    session_id, channel_id, channel_port
                )
                if response:
                    responses.append(response)
            
            elif msg_id == UpperMsg.GetUserInfo:
                # GET_USERINFO请求
                response = self.handle_get_user_info(session_id, account_id)
                if response:
                    responses.append(response)
            
            elif msg_id == UpperMsg.SelectCharacter:
                # SELECT_CHARACTER请求
                # 解析角色槽位（简化，实际格式更复杂）
                character_slot = body[0] if len(body) > 0 else 0
                response = self.handle_select_character(
                    session_id, character_slot, account_id
                )
                if response:
                    responses.append(response)
            
            else:
                # 其他消息暂时忽略
                logger.debug(f"[{session_id}] 未处理的消息: msg_id=0x{msg_id:04x}, body_len={len(body)}")
        
        except Exception as e:
            logger.error(f"[{session_id}] 处理消息失败: msg_id=0x{msg_id:04x}, error={e}")
        
        return responses
    
    def send_initial_notice(
        self,
        session_id: str,
        channel_id: int,
        channel_port: int,
    ) -> bytes:
        """
        发送初始CHANNELINFO通知
        
        Args:
            session_id: 会话ID
            channel_id: 频道ID
            channel_port: 频道端口
            
        Returns:
            通知数据包
        """
        state = self.get_state(session_id)
        state.channel_info_notice_sent = True
        
        body = self.build_channel_info_notice(channel_id, channel_port)
        
        logger.info(f"[{session_id}] 发送CHANNELINFO通知 (channel={channel_id})")
        
        # 使用class0发送通知
        return build_channel_packet(UpperMsg.ChannelInfo, body, 0, classification=0)
