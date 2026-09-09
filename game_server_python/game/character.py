"""
角色系统模块
实现DNF角色的基础数据模型、仓库接口和基本操作
"""

import time
import uuid
from typing import Optional, Dict, List, Tuple, Protocol
from dataclasses import dataclass, field, asdict
from enum import Enum


# 角色槽位限制
DEFAULT_CHARACTER_SLOT_LIMIT = 32


class CharacterError(Exception):
    """角色错误基类"""
    pass


class CharacterIDExistsError(CharacterError):
    """角色ID已存在"""
    pass


class CharacterSlotOccupiedError(CharacterError):
    """角色槽位已被占用"""
    pass


class CharacterNotFoundError(CharacterError):
    """角色未找到"""
    pass


class CharacterNameExistsError(CharacterError):
    """角色名已存在"""
    pass


class Job(Enum):
    """职业枚举"""
    # 基础职业
    SWORDMAN = "swordman"           # 鬼剑士
    FIGHTER = "fighter"             # 格斗家
    GUNNER = "gunner"               # 神枪手
    MAGE = "mage"                   # 魔法师
    PRIEST = "priest"               # 圣职者
    THIEF = "thief"                 # 暗夜使者
    KNIGHT = "knight"               # 守护者
    DEMONIC_LANCER = "demonic_lancer"  # 魔枪士
    GUN_BLADER = "gun_blader"       # 枪剑士
    
    # 转职（鬼剑士）
    SLAYER = "slayer"               # 剑魂
    BERSERKER = "berserker"         # 狂战士
    ASURA = "asura"                 # 阿修罗
    DEVIL_MAY_CRY = "devil_may_cry"  # 鬼泣
    
    # 未知
    UNKNOWN = "unknown"


class CharacterField(Enum):
    """角色字段类型"""
    BASE = "base"
    STATS = "stats"
    LOCATION = "location"
    ROSTER = "roster"


@dataclass
class CharacterLocation:
    """角色位置"""
    channel_id: int = 0
    town_id: int = 0
    dungeon_id: int = 0
    room_id: str = ""


@dataclass
class CharacterRosterHeader:
    """角色列表头部"""
    unk_a: int = 0
    unk_b: int = 0
    total_or_slot_limit: int = 0
    used_or_remain: int = 0
    selected_or_page: int = 0
    roster_state: int = 0
    page_count: int = 0
    roster_flag: int = 0
    roster_value_a: int = 0
    roster_value_b: int = 0


@dataclass
class CharacterRosterEquipSummary:
    """角色装备摘要"""
    slot: int = 0
    item_id_or_icon: int = 0
    raw_entry: bytes = b""
    packed_flags: int = 0
    optional_id_or_expire: int = 0
    aux_value: int = 0
    aux_flag: int = 0


@dataclass
class CharacterRosterEntry:
    """角色列表条目"""
    byte_a: int = 0
    packed_job_grow: int = 0
    byte_c: int = 0
    field_0x2cc: int = 0
    state0: int = 0
    time_a: int = 0
    time_b: int = 0
    equip_summary: List[CharacterRosterEquipSummary] = field(default_factory=list)
    value0: int = 0
    value1: int = 0
    value2: int = 0
    reserved_a: int = 0
    reserved_b: int = 0
    linked_id_block: List[int] = field(default_factory=list)
    value3: int = 0
    object_id: int = 0
    flag0_eq1: int = 0
    special_status_flag: int = 0
    value5: int = 0
    display_flags: int = 0
    reserved_c: int = 0
    reserved_d: int = 0
    value6: int = 0
    flag1_nonzero: int = 0
    bool_a_eq1: int = 0
    bool_b_eq1: int = 0
    bool_c_eq1: int = 0
    flag2_nonzero: int = 0
    flag3_nonzero: int = 0
    flag4_nonzero: int = 0
    flag5_nonzero: int = 0
    value7: int = 0
    flag6_eq1: int = 0
    flags: List[int] = field(default_factory=list)


@dataclass
class CharacterRoster:
    """角色列表"""
    header: CharacterRosterHeader = field(default_factory=CharacterRosterHeader)
    entry: CharacterRosterEntry = field(default_factory=CharacterRosterEntry)


@dataclass
class CharacterRecord:
    """角色记录"""
    character_id: str = ""
    account_id: str = ""
    slot: int = 0
    name: str = ""
    job: str = ""
    level: int = 1
    exp: int = 0
    stats: Dict[str, int] = field(default_factory=dict)
    location: CharacterLocation = field(default_factory=CharacterLocation)
    roster: CharacterRoster = field(default_factory=CharacterRoster)
    created_at: float = 0.0
    updated_at: float = 0.0
    
    def __post_init__(self):
        if not self.character_id:
            self.character_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = time.time()
        if not self.updated_at:
            self.updated_at = time.time()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "character_id": self.character_id,
            "account_id": self.account_id,
            "slot": self.slot,
            "name": self.name,
            "job": self.job,
            "level": self.level,
            "exp": self.exp,
            "stats": self.stats,
            "location": asdict(self.location),
            "roster": {
                "header": asdict(self.roster.header),
                "entry": {
                    **asdict(self.roster.entry),
                    "equip_summary": [asdict(e) for e in self.roster.entry.equip_summary],
                    "linked_id_block": self.roster.entry.linked_id_block,
                    "flags": self.roster.entry.flags,
                },
            },
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CharacterRecord":
        """从字典创建"""
        location_data = data.get("location", {})
        roster_data = data.get("roster", {})
        header_data = roster_data.get("header", {})
        entry_data = roster_data.get("entry", {})
        
        equip_summary = [
            CharacterRosterEquipSummary(**e)
            for e in entry_data.get("equip_summary", [])
        ]
        
        return cls(
            character_id=data.get("character_id", ""),
            account_id=data.get("account_id", ""),
            slot=data.get("slot", 0),
            name=data.get("name", ""),
            job=data.get("job", ""),
            level=data.get("level", 1),
            exp=data.get("exp", 0),
            stats=data.get("stats", {}),
            location=CharacterLocation(**location_data),
            roster=CharacterRoster(
                header=CharacterRosterHeader(**header_data),
                entry=CharacterRosterEntry(
                    **{k: v for k, v in entry_data.items()
                       if k not in ("equip_summary", "linked_id_block", "flags")},
                    equip_summary=equip_summary,
                    linked_id_block=entry_data.get("linked_id_block", []),
                    flags=entry_data.get("flags", []),
                ),
            ),
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
        )


class CharacterRepository(Protocol):
    """角色仓库接口"""
    
    def list_by_account(self, account_id: str, limit: int = DEFAULT_CHARACTER_SLOT_LIMIT) -> List[CharacterRecord]:
        """列出账号下的所有角色"""
        ...
    
    def find_by_id(self, character_id: str) -> Optional[CharacterRecord]:
        """根据ID查找角色"""
        ...
    
    def find_by_name(self, name: str) -> Optional[CharacterRecord]:
        """根据名称查找角色"""
        ...
    
    def create(self, record: CharacterRecord) -> None:
        """创建角色"""
        ...
    
    def update(self, record: CharacterRecord) -> None:
        """更新角色"""
        ...
    
    def delete(self, character_id: str) -> None:
        """删除角色"""
        ...
    
    def next_numeric_id(self) -> int:
        """获取下一个数字ID"""
        ...


class MemoryCharacterRepository:
    """内存角色仓库实现（用于测试）"""
    
    def __init__(self):
        self._characters: Dict[str, CharacterRecord] = {}
        self._numeric_id_counter = 0
    
    def list_by_account(self, account_id: str, limit: int = DEFAULT_CHARACTER_SLOT_LIMIT) -> List[CharacterRecord]:
        """列出账号下的所有角色"""
        characters = [
            char for char in self._characters.values()
            if char.account_id == account_id
        ]
        characters.sort(key=lambda c: c.slot)
        return characters[:limit]
    
    def find_by_id(self, character_id: str) -> Optional[CharacterRecord]:
        """根据ID查找角色"""
        return self._characters.get(character_id)
    
    def find_by_name(self, name: str) -> Optional[CharacterRecord]:
        """根据名称查找角色"""
        for char in self._characters.values():
            if char.name == name:
                return char
        return None
    
    def create(self, record: CharacterRecord) -> None:
        """创建角色"""
        # 检查ID是否存在
        if record.character_id in self._characters:
            raise CharacterIDExistsError(f"Character ID {record.character_id} already exists")
        
        # 检查名称是否存在
        if self.find_by_name(record.name):
            raise CharacterNameExistsError(f"Character name {record.name} already exists")
        
        # 检查槽位是否被占用
        for char in self._characters.values():
            if char.account_id == record.account_id and char.slot == record.slot:
                raise CharacterSlotOccupiedError(f"Slot {record.slot} is occupied")
        
        record.updated_at = time.time()
        self._characters[record.character_id] = record
    
    def update(self, record: CharacterRecord) -> None:
        """更新角色"""
        if record.character_id not in self._characters:
            raise CharacterNotFoundError(f"Character {record.character_id} not found")
        
        record.updated_at = time.time()
        self._characters[record.character_id] = record
    
    def delete(self, character_id: str) -> None:
        """删除角色"""
        if character_id not in self._characters:
            raise CharacterNotFoundError(f"Character {character_id} not found")
        
        del self._characters[character_id]
    
    def next_numeric_id(self) -> int:
        """获取下一个数字ID"""
        self._numeric_id_counter += 1
        return self._numeric_id_counter
    
    def count(self) -> int:
        """获取角色总数"""
        return len(self._characters)
    
    def clear(self) -> None:
        """清空所有角色"""
        self._characters.clear()
        self._numeric_id_counter = 0


class CharacterManager:
    """角色管理器"""
    
    def __init__(self, repository: CharacterRepository):
        self.repository = repository
    
    def create_character(
        self,
        account_id: str,
        name: str,
        job: str,
        slot: int = 0,
        level: int = 1,
    ) -> CharacterRecord:
        """
        创建角色
        
        Args:
            account_id: 账号ID
            name: 角色名
            job: 职业
            slot: 槽位
            level: 等级
            
        Returns:
            创建的角色记录
            
        Raises:
            CharacterNameExistsError: 角色名已存在
            CharacterSlotOccupiedError: 槽位已被占用
        """
        # 检查名称
        if self.repository.find_by_name(name):
            raise CharacterNameExistsError(f"Character name {name} already exists")
        
        # 检查槽位
        account_chars = self.repository.list_by_account(account_id)
        for char in account_chars:
            if char.slot == slot:
                raise CharacterSlotOccupiedError(f"Slot {slot} is occupied")
        
        # 创建角色
        record = CharacterRecord(
            account_id=account_id,
            name=name,
            job=job,
            slot=slot,
            level=level,
        )
        
        # 设置基础属性
        record.stats = self._get_base_stats(job)
        
        self.repository.create(record)
        return record
    
    def delete_character(self, character_id: str) -> None:
        """
        删除角色
        
        Args:
            character_id: 角色ID
            
        Raises:
            CharacterNotFoundError: 角色未找到
        """
        self.repository.delete(character_id)
    
    def get_character(self, character_id: str) -> Optional[CharacterRecord]:
        """获取角色"""
        return self.repository.find_by_id(character_id)
    
    def get_character_by_name(self, name: str) -> Optional[CharacterRecord]:
        """根据名称获取角色"""
        return self.repository.find_by_name(name)
    
    def list_characters(self, account_id: str) -> List[CharacterRecord]:
        """列出账号下的所有角色"""
        return self.repository.list_by_account(account_id)
    
    def update_character(self, record: CharacterRecord) -> None:
        """更新角色"""
        self.repository.update(record)
    
    def level_up(self, character_id: str, levels: int = 1) -> Optional[CharacterRecord]:
        """
        角色升级
        
        Args:
            character_id: 角色ID
            levels: 升级数
            
        Returns:
            更新后的角色记录
        """
        char = self.repository.find_by_id(character_id)
        if not char:
            return None
        
        char.level += levels
        char.updated_at = time.time()
        
        # 更新属性
        self._update_stats_on_level_up(char, levels)
        
        self.repository.update(char)
        return char
    
    def change_job(self, character_id: str, new_job: str) -> Optional[CharacterRecord]:
        """
        转职
        
        Args:
            character_id: 角色ID
            new_job: 新职业
            
        Returns:
            更新后的角色记录
        """
        char = self.repository.find_by_id(character_id)
        if not char:
            return None
        
        char.job = new_job
        char.updated_at = time.time()
        
        self.repository.update(char)
        return char
    
    def swap_slots(self, account_id: str, slot_a: int, slot_b: int) -> None:
        """
        交换两个角色的槽位
        
        Args:
            account_id: 账号ID
            slot_a: 槽位A
            slot_b: 槽位B
        """
        if slot_a == slot_b:
            return
        
        characters = self.repository.list_by_account(account_id)
        char_a = next((c for c in characters if c.slot == slot_a), None)
        char_b = next((c for c in characters if c.slot == slot_b), None)
        
        if char_a and char_b:
            char_a.slot, char_b.slot = slot_b, slot_a
            self.repository.update(char_a)
            self.repository.update(char_b)
    
    def _get_base_stats(self, job: str) -> Dict[str, int]:
        """获取基础属性"""
        base_stats = {
            "hp": 1000,
            "mp": 500,
            "strength": 10,
            "intelligence": 10,
            "vitality": 10,
            "spirit": 10,
            "attack_speed": 10,
            "move_speed": 10,
            "cast_speed": 10,
        }
        
        # 根据职业调整基础属性
        job_stats = {
            Job.SWORDMAN.value: {"strength": 15, "vitality": 12},
            Job.FIGHTER.value: {"strength": 12, "vitality": 15},
            Job.GUNNER.value: {"strength": 10, "attack_speed": 15},
            Job.MAGE.value: {"intelligence": 15, "mp": 800},
            Job.PRIEST.value: {"intelligence": 12, "spirit": 15},
        }
        
        if job in job_stats:
            base_stats.update(job_stats[job])
        
        return base_stats
    
    def _update_stats_on_level_up(self, char: CharacterRecord, levels: int) -> None:
        """升级时更新属性"""
        stat_growth = {
            "hp": 50,
            "mp": 25,
            "strength": 2,
            "intelligence": 2,
            "vitality": 2,
            "spirit": 2,
        }
        
        for stat, growth in stat_growth.items():
            if stat in char.stats:
                char.stats[stat] += growth * levels
