"""
副本系统模块
实现DNF副本数据模型、副本进入、战斗、结算、掉落等
"""

import time
import random
import logging
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


# 日志
logger = logging.getLogger(__name__)


# 副本类型
class DungeonType(Enum):
    """副本类型"""
    NORMAL = "normal"          # 普通副本
    HARD = "hard"              # 困难副本
    EXPERT = "expert"          # 专家副本
    MASTER = "master"          # 王者副本
    SLAYER = "slayer"          # 噩梦副本
    RAID = "raid"              # 团本
    EVENT = "event"            # 活动副本
    TOWER = "tower"            # 塔
    OTHER = "other"            # 其他


# 副本难度
class DungeonDifficulty(Enum):
    """副本难度"""
    EASY = 0       # 简单
    NORMAL = 1     # 普通
    HARD = 2       # 困难
    EXPERT = 3     # 专家
    MASTER = 4     # 王者
    SLAYER = 5     # 噩梦


# 副本状态
class DungeonStatus(Enum):
    """副本状态"""
    NOT_STARTED = 0   # 未开始
    IN_PROGRESS = 1   # 进行中
    PAUSED = 2        # 已暂停
    CLEARED = 3       # 已通关
    FAILED = 4        # 失败
    ABANDONED = 5     # 已放弃


# 房间类型
class RoomType(Enum):
    """房间类型"""
    START = "start"           # 起始房间
    NORMAL = "normal"         # 普通怪物房间
    ELITE = "elite"           # 精英怪物房间
    BOSS = "boss"             # BOSS房间
    TREASURE = "treasure"     # 宝箱房间
    SHOP = "shop"             # 商店房间
    REST = "rest"             # 休息房间
    PUZZLE = "puzzle"         # 谜题房间
    EXIT = "exit"             # 出口房间


@dataclass
class MonsterSpawn:
    """怪物生成配置"""
    monster_id: int = 0
    monster_name: str = ""
    level: int = 1
    count: int = 1
    is_elite: bool = False
    is_boss: bool = False
    
    # 属性倍率
    hp_multiplier: float = 1.0
    attack_multiplier: float = 1.0
    defense_multiplier: float = 1.0
    
    # 掉落配置
    drop_table_id: int = 0
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)


@dataclass
class DungeonRoom:
    """副本房间"""
    room_id: int = 0
    room_type: str = RoomType.NORMAL.value
    room_name: str = ""
    
    # 位置（用于地图显示）
    x: int = 0
    y: int = 0
    
    # 怪物配置
    monsters: List[MonsterSpawn] = field(default_factory=list)
    
    # 连接的房间
    connected_rooms: List[int] = field(default_factory=list)
    
    # 房间状态
    is_cleared: bool = False
    is_locked: bool = False
    
    # 奖励
    exp_reward: int = 0
    gold_reward: int = 0
    item_drops: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        data = asdict(self)
        data['monsters'] = [m.to_dict() for m in self.monsters]
        return data


@dataclass
class DungeonTemplate:
    """副本模板"""
    dungeon_id: int = 0
    dungeon_name: str = ""
    dungeon_type: str = DungeonType.NORMAL.value
    description: str = ""
    
    # 等级限制
    min_level: int = 1
    max_level: int = 100
    recommended_level: int = 1
    
    # 疲劳值消耗
    fatigue_cost: int = 8
    
    # 人数限制
    min_players: int = 1
    max_players: int = 4
    
    # 难度配置
    available_difficulties: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    
    # 房间配置
    rooms: List[DungeonRoom] = field(default_factory=list)
    start_room_id: int = 0
    boss_room_id: int = 0
    
    # 通关奖励
    clear_exp: int = 0
    clear_gold: int = 0
    clear_items: List[Dict[str, Any]] = field(default_factory=list)
    
    # 掉落表
    drop_table_id: int = 0
    
    # 地图信息
    map_id: int = 0
    map_name: str = ""
    
    # 前置副本
    prerequisite_dungeons: List[int] = field(default_factory=list)
    
    # 每日进入限制
    daily_entry_limit: int = 0  # 0表示不限制
    
    # 副本分类
    category: str = ""
    sub_category: str = ""
    
    def to_dict(self) -> dict:
        """转换为字典"""
        data = asdict(self)
        data['rooms'] = [r.to_dict() for r in self.rooms]
        return data


@dataclass
class DungeonSession:
    """副本会话（进行中的副本）"""
    session_id: int = 0
    dungeon_id: int = 0
    dungeon_name: str = ""
    difficulty: int = DungeonDifficulty.NORMAL.value
    status: int = DungeonStatus.NOT_STARTED.value
    
    # 玩家信息
    character_id: str = ""
    character_name: str = ""
    character_level: int = 1
    
    # 队伍信息
    party_id: int = 0
    party_members: List[str] = field(default_factory=list)
    
    # 当前进度
    current_room_id: int = 0
    cleared_rooms: List[int] = field(default_factory=list)
    total_rooms: int = 0
    
    # 战斗统计
    monsters_killed: int = 0
    damage_dealt: int = 0
    damage_taken: int = 0
    deaths: int = 0
    resurrection_used: int = 0
    
    # 时间
    start_time: float = 0.0
    end_time: float = 0.0
    pause_time: float = 0.0
    total_pause_time: float = 0.0
    
    # 获得的奖励（临时存储，通关后发放）
    pending_exp: int = 0
    pending_gold: int = 0
    pending_items: List[Dict[str, Any]] = field(default_factory=list)
    
    # 额外数据
    extra_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.start_time:
            self.start_time = time.time()
    
    @property
    def is_in_progress(self) -> bool:
        """是否进行中"""
        return self.status == DungeonStatus.IN_PROGRESS.value
    
    @property
    def is_cleared(self) -> bool:
        """是否已通关"""
        return self.status == DungeonStatus.CLEARED.value
    
    @property
    def elapsed_time(self) -> float:
        """已用时间（秒）"""
        if self.end_time:
            return self.end_time - self.start_time - self.total_pause_time
        return time.time() - self.start_time - self.total_pause_time
    
    @property
    def clear_progress(self) -> float:
        """通关进度（0-1）"""
        if self.total_rooms <= 0:
            return 0.0
        return len(self.cleared_rooms) / self.total_rooms
    
    def enter_room(self, room_id: int) -> bool:
        """进入房间"""
        self.current_room_id = room_id
        return True
    
    def clear_room(self, room_id: int) -> bool:
        """清除房间"""
        if room_id not in self.cleared_rooms:
            self.cleared_rooms.append(room_id)
        return True
    
    def pause(self) -> bool:
        """暂停"""
        if self.is_in_progress:
            self.status = DungeonStatus.PAUSED.value
            self.pause_time = time.time()
            return True
        return False
    
    def resume(self) -> bool:
        """恢复"""
        if self.status == DungeonStatus.PAUSED.value:
            self.status = DungeonStatus.IN_PROGRESS.value
            self.total_pause_time += time.time() - self.pause_time
            self.pause_time = 0
            return True
        return False
    
    def clear(self) -> bool:
        """通关"""
        self.status = DungeonStatus.CLEARED.value
        self.end_time = time.time()
        return True
    
    def fail(self) -> bool:
        """失败"""
        self.status = DungeonStatus.FAILED.value
        self.end_time = time.time()
        return True
    
    def abandon(self) -> bool:
        """放弃"""
        self.status = DungeonStatus.ABANDONED.value
        self.end_time = time.time()
        return True
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "dungeon_id": self.dungeon_id,
            "dungeon_name": self.dungeon_name,
            "difficulty": self.difficulty,
            "status": self.status,
            "character_id": self.character_id,
            "character_name": self.character_name,
            "character_level": self.character_level,
            "current_room_id": self.current_room_id,
            "cleared_rooms": self.cleared_rooms,
            "total_rooms": self.total_rooms,
            "monsters_killed": self.monsters_killed,
            "damage_dealt": self.damage_dealt,
            "damage_taken": self.damage_taken,
            "deaths": self.deaths,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "elapsed_time": self.elapsed_time,
            "clear_progress": self.clear_progress,
            "pending_exp": self.pending_exp,
            "pending_gold": self.pending_gold,
            "pending_items": self.pending_items,
        }


@dataclass
class DungeonRecord:
    """副本通关记录"""
    record_id: int = 0
    character_id: str = ""
    dungeon_id: int = 0
    dungeon_name: str = ""
    difficulty: int = 0
    
    # 通关时间
    clear_time: float = 0.0
    clear_date: float = 0.0
    
    # 评分
    rank: str = "C"  # S, A, B, C, D, F
    score: int = 0
    
    # 统计
    monsters_killed: int = 0
    deaths: int = 0
    
    # 奖励
    exp_gained: int = 0
    gold_gained: int = 0
    items_gained: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.clear_date:
            self.clear_date = time.time()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)


class DungeonManager:
    """副本管理器"""
    
    def __init__(self):
        # 副本模板（dungeon_id -> DungeonTemplate）
        self._dungeon_templates: Dict[int, DungeonTemplate] = {}
        
        # 进行中的副本会话（session_id -> DungeonSession）
        self._active_sessions: Dict[int, DungeonSession] = {}
        
        # 角色当前副本（character_id -> session_id）
        self._character_sessions: Dict[str, int] = {}
        
        # 通关记录（character_id -> [DungeonRecord]）
        self._clear_records: Dict[str, List[DungeonRecord]] = {}
        
        # 每日进入次数（character_id -> {dungeon_id: count}）
        self._daily_entries: Dict[str, Dict[int, int]] = {}
        
        # 会话ID计数器
        self._session_id_counter = 0
    
    def register_dungeon_template(self, dungeon: DungeonTemplate) -> None:
        """注册副本模板"""
        self._dungeon_templates[dungeon.dungeon_id] = dungeon
        logger.info(f"注册副本: {dungeon.dungeon_name} (ID={dungeon.dungeon_id})")
    
    def get_dungeon_template(self, dungeon_id: int) -> Optional[DungeonTemplate]:
        """获取副本模板"""
        return self._dungeon_templates.get(dungeon_id)
    
    def get_all_dungeons(self) -> List[DungeonTemplate]:
        """获取所有副本"""
        return list(self._dungeon_templates.values())
    
    def get_available_dungeons(
        self,
        character_level: int = 1,
        character_id: str = "",
    ) -> List[DungeonTemplate]:
        """
        获取角色可进入的副本列表
        
        Args:
            character_level: 角色等级
            character_id: 角色ID
            
        Returns:
            可进入的副本列表
        """
        available = []
        completed_dungeons = set()
        
        # 获取已通关的副本（用于前置检查）
        if character_id and character_id in self._clear_records:
            for record in self._clear_records[character_id]:
                completed_dungeons.add(record.dungeon_id)
        
        for dungeon in self._dungeon_templates.values():
            # 等级限制
            if character_level < dungeon.min_level or character_level > dungeon.max_level:
                continue
            
            # 前置副本检查
            prerequisites_met = all(
                pre_dungeon_id in completed_dungeons
                for pre_dungeon_id in dungeon.prerequisite_dungeons
            )
            if not prerequisites_met:
                continue
            
            # 每日进入限制检查
            if dungeon.daily_entry_limit > 0 and character_id:
                daily_count = self._daily_entries.get(character_id, {}).get(dungeon.dungeon_id, 0)
                if daily_count >= dungeon.daily_entry_limit:
                    continue
            
            available.append(dungeon)
        
        return available
    
    def can_enter_dungeon(
        self,
        character_id: str,
        dungeon_id: int,
        character_level: int = 1,
        difficulty: int = 0,
        current_fatigue: int = 156,
    ) -> Tuple[bool, str]:
        """
        检查是否可以进入副本
        
        Returns:
            (是否可以, 原因)
        """
        template = self.get_dungeon_template(dungeon_id)
        if not template:
            return False, "副本不存在"
        
        # 检查是否已有进行中的副本
        if character_id in self._character_sessions:
            return False, "已有进行中的副本"
        
        # 等级限制
        if character_level < template.min_level:
            return False, f"等级不足（需要{template.min_level}级）"
        if character_level > template.max_level:
            return False, f"等级超过限制（最高{template.max_level}级）"
        
        # 难度检查
        if difficulty not in template.available_difficulties:
            return False, "该难度不可用"
        
        # 疲劳值检查
        if current_fatigue < template.fatigue_cost:
            return False, f"疲劳值不足（需要{template.fatigue_cost}点）"
        
        # 每日进入限制
        if template.daily_entry_limit > 0:
            daily_count = self._daily_entries.get(character_id, {}).get(dungeon_id, 0)
            if daily_count >= template.daily_entry_limit:
                return False, "今日进入次数已用完"
        
        # 前置副本检查
        completed_dungeons = set()
        if character_id in self._clear_records:
            for record in self._clear_records[character_id]:
                completed_dungeons.add(record.dungeon_id)
        
        for pre_dungeon_id in template.prerequisite_dungeons:
            if pre_dungeon_id not in completed_dungeons:
                pre_template = self.get_dungeon_template(pre_dungeon_id)
                pre_name = pre_template.dungeon_name if pre_template else f"副本{pre_dungeon_id}"
                return False, f"需要先通关副本：{pre_name}"
        
        return True, ""
    
    def enter_dungeon(
        self,
        character_id: str,
        character_name: str,
        character_level: int,
        dungeon_id: int,
        difficulty: int = 0,
    ) -> Tuple[bool, str, Optional[DungeonSession]]:
        """
        进入副本
        
        Returns:
            (是否成功, 原因, 副本会话)
        """
        # 检查是否可以进入
        can_enter, reason = self.can_enter_dungeon(
            character_id, dungeon_id, character_level, difficulty
        )
        if not can_enter:
            return False, reason, None
        
        template = self.get_dungeon_template(dungeon_id)
        
        # 创建副本会话
        self._session_id_counter += 1
        session = DungeonSession(
            session_id=self._session_id_counter,
            dungeon_id=dungeon_id,
            dungeon_name=template.dungeon_name,
            difficulty=difficulty,
            status=DungeonStatus.IN_PROGRESS.value,
            character_id=character_id,
            character_name=character_name,
            character_level=character_level,
            current_room_id=template.start_room_id,
            total_rooms=len(template.rooms),
        )
        
        # 保存会话
        self._active_sessions[session.session_id] = session
        self._character_sessions[character_id] = session.session_id
        
        # 记录每日进入次数
        if character_id not in self._daily_entries:
            self._daily_entries[character_id] = {}
        self._daily_entries[character_id][dungeon_id] = \
            self._daily_entries[character_id].get(dungeon_id, 0) + 1
        
        logger.info(f"角色{character_name}进入副本: {template.dungeon_name} (难度: {difficulty})")
        
        return True, "", session
    
    def get_active_session(self, character_id: str) -> Optional[DungeonSession]:
        """获取角色当前的副本会话"""
        session_id = self._character_sessions.get(character_id)
        if session_id:
            return self._active_sessions.get(session_id)
        return None
    
    def get_session_by_id(self, session_id: int) -> Optional[DungeonSession]:
        """根据会话ID获取副本会话"""
        return self._active_sessions.get(session_id)
    
    def enter_room(self, character_id: str, room_id: int) -> Tuple[bool, str]:
        """进入房间"""
        session = self.get_active_session(character_id)
        if not session or not session.is_in_progress:
            return False, "没有进行中的副本"
        
        template = self.get_dungeon_template(session.dungeon_id)
        if not template:
            return False, "副本模板不存在"
        
        # 检查房间是否存在
        room = next((r for r in template.rooms if r.room_id == room_id), None)
        if not room:
            return False, "房间不存在"
        
        # 检查房间是否已清除
        if room_id not in session.cleared_rooms:
            # 检查是否可以进入（需要清除前置房间）
            # 简化处理：允许进入任何已连接的房间
            pass
        
        session.enter_room(room_id)
        logger.info(f"角色{character_id}进入房间: {room_id}")
        
        return True, ""
    
    def clear_room(self, character_id: str, room_id: int) -> Tuple[bool, str]:
        """清除房间"""
        session = self.get_active_session(character_id)
        if not session or not session.is_in_progress:
            return False, "没有进行中的副本"
        
        template = self.get_dungeon_template(session.dungeon_id)
        if not template:
            return False, "副本模板不存在"
        
        room = next((r for r in template.rooms if r.room_id == room_id), None)
        if not room:
            return False, "房间不存在"
        
        # 清除房间
        session.clear_room(room_id)
        
        # 累加房间奖励
        session.pending_exp += room.exp_reward
        session.pending_gold += room.gold_reward
        session.pending_items.extend(room.item_drops)
        
        # 检查是否是BOSS房间，如果是则通关
        if room_id == template.boss_room_id:
            self._clear_dungeon(session)
        
        logger.info(f"角色{character_id}清除房间: {room_id}")
        
        return True, ""
    
    def _clear_dungeon(self, session: DungeonSession) -> bool:
        """通关副本（内部方法）"""
        template = self.get_dungeon_template(session.dungeon_id)
        if not template:
            return False
        
        # 计算难度倍率
        difficulty_multiplier = 1.0 + session.difficulty * 0.2
        
        # 累加通关奖励
        session.pending_exp += int(template.clear_exp * difficulty_multiplier)
        session.pending_gold += int(template.clear_gold * difficulty_multiplier)
        session.pending_items.extend(template.clear_items)
        
        # 通关
        session.clear()
        
        # 生成通关记录
        record = DungeonRecord(
            character_id=session.character_id,
            dungeon_id=session.dungeon_id,
            dungeon_name=session.dungeon_name,
            difficulty=session.difficulty,
            clear_time=session.elapsed_time,
            monsters_killed=session.monsters_killed,
            deaths=session.deaths,
            exp_gained=session.pending_exp,
            gold_gained=session.pending_gold,
            items_gained=session.pending_items,
        )
        
        # 计算评分
        record.score = self._calculate_score(session)
        record.rank = self._calculate_rank(record.score)
        
        # 保存记录
        if session.character_id not in self._clear_records:
            self._clear_records[session.character_id] = []
        self._clear_records[session.character_id].append(record)
        
        logger.info(f"角色{session.character_name}通关副本: {session.dungeon_name} (评分: {record.rank})")
        
        return True
    
    def _calculate_score(self, session: DungeonSession) -> int:
        """计算通关评分"""
        # 基础分1000
        score = 1000
        
        # 时间奖励（越快越高）
        if session.elapsed_time < 60:
            score += 500
        elif session.elapsed_time < 120:
            score += 300
        elif session.elapsed_time < 180:
            score += 100
        
        # 死亡惩罚
        score -= session.deaths * 200
        
        # 被击惩罚
        score -= min(session.damage_taken // 100, 200)
        
        return max(0, score)
    
    def _calculate_rank(self, score: int) -> str:
        """根据分数计算评级"""
        if score >= 1800:
            return "S"
        elif score >= 1500:
            return "A"
        elif score >= 1200:
            return "B"
        elif score >= 900:
            return "C"
        elif score >= 600:
            return "D"
        else:
            return "F"
    
    def claim_rewards(self, character_id: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        领取副本奖励
        
        Returns:
            (是否成功, 原因, 奖励)
        """
        session = self.get_active_session(character_id)
        if not session:
            return False, "没有进行中的副本", None
        
        if not session.is_cleared:
            return False, "副本未通关", None
        
        rewards = {
            "exp": session.pending_exp,
            "gold": session.pending_gold,
            "items": session.pending_items,
        }
        
        # 清理会话
        self._cleanup_session(character_id)
        
        logger.info(f"角色{character_id}领取副本奖励: 经验={rewards['exp']}, 金币={rewards['gold']}")
        
        return True, "", rewards
    
    def abandon_dungeon(self, character_id: str) -> Tuple[bool, str]:
        """放弃副本"""
        session = self.get_active_session(character_id)
        if not session or not session.is_in_progress:
            return False, "没有进行中的副本"
        
        session.abandon()
        self._cleanup_session(character_id)
        
        logger.info(f"角色{character_id}放弃副本: {session.dungeon_name}")
        
        return True, ""
    
    def fail_dungeon(self, character_id: str) -> Tuple[bool, str]:
        """副本失败"""
        session = self.get_active_session(character_id)
        if not session or not session.is_in_progress:
            return False, "没有进行中的副本"
        
        session.fail()
        self._cleanup_session(character_id)
        
        logger.info(f"角色{character_id}副本失败: {session.dungeon_name}")
        
        return True, ""
    
    def _cleanup_session(self, character_id: str) -> None:
        """清理副本会话"""
        session_id = self._character_sessions.pop(character_id, None)
        if session_id:
            # 延迟删除，保留一段时间用于查询
            pass
    
    def get_clear_records(self, character_id: str) -> List[DungeonRecord]:
        """获取角色通关记录"""
        return self._clear_records.get(character_id, [])
    
    def get_dungeon_clear_count(self, character_id: str, dungeon_id: int) -> int:
        """获取角色指定副本的通关次数"""
        records = self.get_clear_records(character_id)
        return sum(1 for r in records if r.dungeon_id == dungeon_id)
    
    def reset_daily_entries(self) -> int:
        """重置每日进入次数"""
        count = len(self._daily_entries)
        self._daily_entries.clear()
        logger.info(f"重置每日进入次数，影响{count}个角色")
        return count
    
    def to_dict(self, character_id: str) -> dict:
        """转换为字典"""
        session = self.get_active_session(character_id)
        records = self.get_clear_records(character_id)
        
        return {
            "character_id": character_id,
            "active_session": session.to_dict() if session else None,
            "clear_records": [r.to_dict() for r in records],
            "clear_count": len(records),
        }
