"""
场景初始化模块
实现DNF角色选择后的场景初始化流程：角色选择确认 → 玩家状态 → 场景对象 → 进入城镇
"""

import struct
import time
import logging
from typing import Optional, List, Tuple
from dataclasses import dataclass, field

from protocol.channel_packet import build_channel_packet
from game.bootstrap import PacketWriter, UpperMsg
from game.character import CharacterRecord


# 日志
logger = logging.getLogger(__name__)


# 场景消息ID
class SceneMsg:
    """场景相关消息ID"""
    # 角色选择确认
    SelectCharacterAck = 0x0009
    
    # 玩家状态
    PlayerState = 0x000A
    PlayerInfo = 0x000B
    
    # 场景对象
    SceneObjectList = 0x000C
    SceneObjectAdd = 0x000D
    SceneObjectRemove = 0x000E
    
    # 进入城镇
    EnterTown = 0x000F
    TownPosition = 0x0010
    
    # 背包/装备
    InventoryList = 0x0011
    EquipmentList = 0x0012
    
    # 技能
    SkillList = 0x0013
    
    # 任务
    QuestList = 0x0014
    
    # 疲劳值
    FatigueState = 0x0024
    
    # 场景加载完成
    FinishLoading = 0x0015
    
    # 城镇UI就绪
    TownUIReady = 0x0016


# 城镇ID
class TownID:
    """城镇ID"""
    # 艾尔文防线
    Elvengard = 1
    # 赫顿玛尔
    Hendonmyre = 2
    # 西海岸
    WestCoast = 3
    # 斯顿雪域
    SnowyValley = 4
    # 暗黑城
    Underfoot = 5
    # 诺斯玛尔
    Northmyre = 6
    # 神之都根特
    Ghent = 7
    # 鲁夫特悬空海港
    Airport = 8
    # 时空之门
    TimeGate = 9
    # 能源中心
    PowerStation = 10
    # 寂静城
    SilentCity = 11
    # 魔界
    Metropolis = 12


@dataclass
class SceneState:
    """场景状态"""
    # 角色选择状态
    select_ack_sent: bool = False
    character_selected: bool = False
    
    # 场景初始化状态
    player_state_sent: bool = False
    scene_objects_sent: bool = False
    inventory_sent: bool = False
    skills_sent: bool = False
    quests_sent: bool = False
    
    # 城镇状态
    town_entered: bool = False
    town_id: int = TownID.Hendonmyre
    town_position_x: float = 0.0
    town_position_y: float = 0.0
    
    # 加载状态
    loading_finished: bool = False
    town_ui_ready: bool = False
    
    # 时间戳
    select_time: float = 0.0
    enter_town_time: float = 0.0


class SceneInitializer:
    """
    场景初始化器
    
    处理角色选择后的场景初始化流程
    """
    
    def __init__(self, server_ip: str = "127.0.0.1"):
        """
        初始化场景初始化器
        
        Args:
            server_ip: 服务器IP
        """
        self.server_ip = server_ip
        
        # 会话状态（按会话ID存储）
        self._states: dict = {}
    
    def get_state(self, session_id: str) -> SceneState:
        """获取会话状态"""
        if session_id not in self._states:
            self._states[session_id] = SceneState()
        return self._states[session_id]
    
    def remove_state(self, session_id: str) -> None:
        """移除会话状态"""
        if session_id in self._states:
            del self._states[session_id]
    
    def build_select_character_ack(
        self,
        character: CharacterRecord,
        character_id: int,
        selected_slot: int,
        account_cera: int = 0,
    ) -> bytes:
        """
        构建角色选择确认包
        
        Args:
            character: 角色记录
            character_id: 角色ID
            selected_slot: 选中的槽位
            account_cera: 账号点券
            
        Returns:
            角色选择确认包体
        """
        writer = PacketWriter()
        
        # 基础信息
        writer.write_byte(1)  # 固定
        writer.write_uint32(0)  # 账号注册时间（未使用）
        writer.write_uint32(int(character.created_at))  # 角色创建时间
        writer.write_uint16(character_id)  # 角色ID
        
        # 疲劳值状态
        fatigue_used = character.stats.get('fatigue_used', 0)
        fatigue_limit = character.stats.get('fatigue_limit', 156)
        writer.write_uint16(fatigue_used)  # 已用疲劳
        writer.write_uint16(fatigue_limit)  # 疲劳上限
        writer.write_uint16(0)  # 疲劳辅助值
        
        # 高级服务条目（空）
        writer.write_byte(0)  # 高级服务数量
        
        # 点券
        writer.write_uint32(account_cera)
        
        # 任务列表（30个固定槽位）
        for _ in range(30):
            writer.write_uint16(0xFFFF)  # 任务ID（空）
            writer.write_uint32(0)  # 触发值
        
        # 溢出任务数量
        writer.write_uint32(0)
        
        # 状态值（4个u32）
        for _ in range(4):
            writer.write_uint32(0)
        
        # 选中的角色槽位
        writer.write_byte(selected_slot & 0xFF)
        
        # 教程状态
        writer.write_byte(0)  # 教程状态（未使用）
        tutorial_completed = character.stats.get('tutorial_completed', 1)
        if tutorial_completed:
            writer.write_byte(1)  # 有教程索引
            writer.write_byte(31)  # 教程索引（城镇路线）
        else:
            writer.write_byte(0)  # 无教程索引
        
        # 疲劳电池
        writer.write_uint16(character.stats.get('fatigue_battery', 0))
        
        # 显示已用疲劳
        writer.write_uint16(fatigue_used)
        
        # 交易惩罚标记
        writer.write_byte(character.stats.get('trade_punish_flag', 0))
        
        # 疲劳额外值
        writer.write_uint16(character.stats.get('fatigue_grownup_buff', 0))
        
        # 结束
        writer.write_byte(0)  # 次级列表数量
        
        return writer.get_bytes()
    
    def build_player_state(self, character: CharacterRecord) -> bytes:
        """
        构建玩家状态包
        
        Args:
            character: 角色记录
            
        Returns:
            玩家状态包体
        """
        writer = PacketWriter()
        
        # 角色基础信息
        writer.write_uint32(character.level)  # 等级
        writer.write_uint32(character.exp)  # 经验值
        
        # 属性
        writer.write_uint16(character.stats.get('strength', 10))  # 力量
        writer.write_uint16(character.stats.get('intelligence', 10))  # 智力
        writer.write_uint16(character.stats.get('vitality', 10))  # 体力
        writer.write_uint16(character.stats.get('spirit', 10))  # 精神
        
        # HP/MP
        writer.write_uint32(character.stats.get('hp', 1000))  # 当前HP
        writer.write_uint32(character.stats.get('hp_max', 1000))  # 最大HP
        writer.write_uint32(character.stats.get('mp', 500))  # 当前MP
        writer.write_uint32(character.stats.get('mp_max', 500))  # 最大MP
        
        # 攻击/防御
        writer.write_uint32(character.stats.get('physical_attack', 100))  # 物理攻击
        writer.write_uint32(character.stats.get('magical_attack', 100))  # 魔法攻击
        writer.write_uint32(character.stats.get('physical_defense', 100))  # 物理防御
        writer.write_uint32(character.stats.get('magical_defense', 100))  # 魔法防御
        
        # 速度
        writer.write_uint16(character.stats.get('attack_speed', 1000))  # 攻击速度
        writer.write_uint16(character.stats.get('move_speed', 1000))  # 移动速度
        writer.write_uint16(character.stats.get('cast_speed', 1000))  # 施放速度
        
        # 暴击
        writer.write_uint16(character.stats.get('physical_critical', 0))  # 物理暴击
        writer.write_uint16(character.stats.get('magical_critical', 0))  # 魔法暴击
        
        # 命中率/回避率
        writer.write_uint16(character.stats.get('hit_rate', 0))  # 命中率
        writer.write_uint16(character.stats.get('evasion_rate', 0))  # 回避率
        
        return writer.get_bytes()
    
    def build_scene_object_list(self, character: CharacterRecord) -> bytes:
        """
        构建场景对象列表包
        
        Args:
            character: 角色记录
            
        Returns:
            场景对象列表包体
        """
        writer = PacketWriter()
        
        # 对象数量
        writer.write_uint16(1)  # 只有玩家自己
        
        # 玩家对象
        writer.write_uint32(character.selected_character_id if hasattr(character, 'selected_character_id') else 1)  # 对象ID
        writer.write_byte(1)  # 对象类型（玩家）
        
        # 位置
        writer.write_uint32(int(character.location.town_id))  # 城镇ID
        writer.write_uint32(0)  # X坐标
        writer.write_uint32(0)  # Y坐标
        
        # 外观（简化）
        writer.write_uint32(0)  # 头发
        writer.write_uint32(0)  # 帽子
        writer.write_uint32(0)  # 脸
        writer.write_uint32(0)  # 皮肤
        
        # 职业
        job_id = self._job_to_id(character.job)
        writer.write_uint16(job_id)  # 职业
        writer.write_uint16(0)  # 转职
        
        # 等级
        writer.write_uint16(character.level)
        
        # 名称
        writer.write_utf16_dstr(character.name)
        
        # 公会名称（空）
        writer.write_utf16_dstr("")
        
        return writer.get_bytes()
    
    def build_inventory_list(self, character: CharacterRecord) -> bytes:
        """
        构建背包列表包（简化，空背包）
        
        Args:
            character: 角色记录
            
        Returns:
            背包列表包体
        """
        writer = PacketWriter()
        
        # 背包类型数量
        writer.write_byte(5)  # 5种背包（装备/消耗品/材料/任务/副职）
        
        # 每种背包
        for inv_type in range(5):
            writer.write_byte(inv_type)  # 背包类型
            writer.write_uint16(0)  # 物品数量
            writer.write_uint16(64)  # 背包容量
        
        return writer.get_bytes()
    
    def build_skill_list(self, character: CharacterRecord) -> bytes:
        """
        构建技能列表包（简化，空技能）
        
        Args:
            character: 角色记录
            
        Returns:
            技能列表包体
        """
        writer = PacketWriter()
        
        # 技能数量
        writer.write_uint16(0)
        
        # 快捷技能栏
        for _ in range(12):
            writer.write_uint32(0)  # 技能ID
        
        return writer.get_bytes()
    
    def build_quest_list(self, character: CharacterRecord) -> bytes:
        """
        构建任务列表包（简化，空任务）
        
        Args:
            character: 角色记录
            
        Returns:
            任务列表包体
        """
        writer = PacketWriter()
        
        # 进行中任务数量
        writer.write_uint16(0)
        
        # 已完成任务数量
        writer.write_uint16(0)
        
        return writer.get_bytes()
    
    def build_enter_town(self, character: CharacterRecord, town_id: int) -> bytes:
        """
        构建进入城镇包
        
        Args:
            character: 角色记录
            town_id: 城镇ID
            
        Returns:
            进入城镇包体
        """
        writer = PacketWriter()
        
        # 城镇ID
        writer.write_uint32(town_id)
        
        # 频道ID
        writer.write_uint16(1)
        
        # 位置
        writer.write_uint32(0)  # X坐标
        writer.write_uint32(0)  # Y坐标
        
        # 方向
        writer.write_byte(0)
        
        return writer.get_bytes()
    
    def build_fatigue_state(self, character: CharacterRecord) -> bytes:
        """
        构建疲劳值状态包
        
        Args:
            character: 角色记录
            
        Returns:
            疲劳值状态包体
        """
        writer = PacketWriter()
        
        fatigue_used = character.stats.get('fatigue_used', 0)
        fatigue_limit = character.stats.get('fatigue_limit', 156)
        
        writer.write_uint16(fatigue_used)  # 已用疲劳
        writer.write_uint16(fatigue_limit)  # 疲劳上限
        writer.write_uint16(0)  # 疲劳辅助
        writer.write_uint16(fatigue_used)  # 显示已用
        writer.write_uint16(0)  # 疲劳额外
        
        return writer.get_bytes()
    
    def initialize_scene(
        self,
        session_id: str,
        character: CharacterRecord,
        character_id: int,
        selected_slot: int,
        account_cera: int = 0,
    ) -> List[Tuple[int, bytes]]:
        """
        初始化场景，返回需要发送的数据包列表
        
        Args:
            session_id: 会话ID
            character: 角色记录
            character_id: 角色ID
            selected_slot: 选中的槽位
            account_cera: 账号点券
            
        Returns:
            (消息ID, 包体) 列表
        """
        state = self.get_state(session_id)
        state.character_selected = True
        state.select_time = time.time()
        
        packets = []
        
        # 1. 角色选择确认
        select_ack = self.build_select_character_ack(
            character, character_id, selected_slot, account_cera
        )
        packets.append((UpperMsg.SelectCharacter, select_ack))
        state.select_ack_sent = True
        
        # 2. 玩家状态
        player_state = self.build_player_state(character)
        packets.append((SceneMsg.PlayerState, player_state))
        state.player_state_sent = True
        
        # 3. 场景对象列表
        scene_objects = self.build_scene_object_list(character)
        packets.append((SceneMsg.SceneObjectList, scene_objects))
        state.scene_objects_sent = True
        
        # 4. 背包列表
        inventory = self.build_inventory_list(character)
        packets.append((SceneMsg.InventoryList, inventory))
        state.inventory_sent = True
        
        # 5. 技能列表
        skills = self.build_skill_list(character)
        packets.append((SceneMsg.SkillList, skills))
        state.skills_sent = True
        
        # 6. 任务列表
        quests = self.build_quest_list(character)
        packets.append((SceneMsg.QuestList, quests))
        state.quests_sent = True
        
        # 7. 疲劳值状态
        fatigue = self.build_fatigue_state(character)
        packets.append((SceneMsg.FatigueState, fatigue))
        
        # 8. 进入城镇
        town_id = character.location.town_id or TownID.Hendonmyre
        enter_town = self.build_enter_town(character, town_id)
        packets.append((SceneMsg.EnterTown, enter_town))
        state.town_entered = True
        state.town_id = town_id
        state.enter_town_time = time.time()
        
        logger.info(
            f"[{session_id}] 场景初始化完成 "
            f"(character={character.name}, town={town_id}, packets={len(packets)})"
        )
        
        return packets
    
    def handle_finish_loading(self, session_id: str) -> Optional[bytes]:
        """
        处理场景加载完成
        
        Args:
            session_id: 会话ID
            
        Returns:
            响应数据包（如果需要）
        """
        state = self.get_state(session_id)
        state.loading_finished = True
        
        logger.info(f"[{session_id}] 场景加载完成")
        
        return None
    
    def handle_town_ui_ready(self, session_id: str) -> Optional[bytes]:
        """
        处理城镇UI就绪
        
        Args:
            session_id: 会话ID
            
        Returns:
            响应数据包（如果需要）
        """
        state = self.get_state(session_id)
        state.town_ui_ready = True
        
        logger.info(f"[{session_id}] 城镇UI就绪")
        
        return None
    
    def _job_to_id(self, job: str) -> int:
        """职业名称转ID"""
        job_map = {
            'swordman': 0,
            'fighter': 1,
            'gunner': 2,
            'mage': 3,
            'priest': 4,
            'thief': 5,
            'knight': 6,
            'demonic_lancer': 7,
            'gun_blader': 8,
        }
        return job_map.get(job.lower(), 0)
