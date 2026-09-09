"""
物品系统模块
实现DNF物品数据模型、背包、仓库、物品操作等
"""

import time
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum


# 日志
logger = logging.getLogger(__name__)


# 物品类型
class ItemType(Enum):
    """物品类型"""
    EQUIPMENT = "equipment"        # 装备
    CONSUMABLE = "consumable"      # 消耗品
    MATERIAL = "material"          # 材料
    QUEST = "quest"                # 任务物品
    PROFESSION = "profession"      # 副职物品
    CARD = "card"                  # 卡片
    AVATAR = "avatar"              # 装扮
    CREATURE = "creature"          # 宠物
    TITLE = "title"                # 称号
    OTHER = "other"                # 其他


# 装备部位
class EquipSlot(Enum):
    """装备部位"""
    WEAPON = 0          # 武器
    COAT = 1            # 上衣
    PANTS = 2           # 下装
    HEAD = 3            # 头肩
    WAIST = 4           # 腰带
    SHOES = 5           # 鞋
    NECKLACE = 6        # 项链
    BRACELET = 7        # 手镯
    RING = 8            # 戒指
    AUXILIARY = 9       # 辅助装备
    MAGIC_STONE = 10    # 魔法石
    EARRING = 11        # 耳环
    TITLE = 12          # 称号
    PET = 13            # 宠物
    AVATAR_HAT = 14     # 帽子
    AVATAR_FACE = 15    # 脸部
    AVATAR_NECK = 16    # 胸部
    AVATAR_COAT = 17    # 上衣
    AVATAR_PANTS = 18   # 下装
    AVATAR_WAIST = 19   # 腰带
    AVATAR_SHOES = 20   # 鞋
    AVATAR_SKIN = 21    # 皮肤
    AURA = 22           # 光环
    WEAPON_AVATAR = 23  # 武器装扮


# 稀有度
class Rarity(Enum):
    """稀有度"""
    COMMON = 0          # 普通（白）
    UNCOMMON = 1        # 高级（蓝）
    RARE = 2            # 稀有（紫）
    EPIC = 3            # 史诗（粉）
    LEGENDARY = 4       # 传说（橙）
    MYTHIC = 5          # 神话（红）
    ANCIENT = 6         # 远古
    OTHER = 7           # 其他


# 背包类型
class InventoryType(Enum):
    """背包类型"""
    EQUIPMENT = 0       # 装备栏
    CONSUMABLE = 1      # 消耗品栏
    MATERIAL = 2        # 材料栏
    QUEST = 3           # 任务栏
    PROFESSION = 4      # 副职栏
    SHORTCUT = 5        # 快捷栏


@dataclass
class ItemRecord:
    """物品记录"""
    item_id: int = 0
    item_name: str = ""
    item_type: str = ItemType.OTHER.value
    rarity: int = Rarity.COMMON.value
    level: int = 0
    description: str = ""
    icon_path: str = ""
    
    # 消耗品属性
    cooldown: float = 0.0
    stackable: bool = False
    max_stack: int = 1
    
    # 装备属性
    equip_slot: int = -1
    job_required: List[str] = field(default_factory=list)
    level_required: int = 0
    
    # 基础属性
    strength: int = 0
    intelligence: int = 0
    vitality: int = 0
    spirit: int = 0
    hp_max: int = 0
    mp_max: int = 0
    physical_attack: int = 0
    magical_attack: int = 0
    physical_defense: int = 0
    magical_defense: int = 0
    attack_speed: int = 0
    move_speed: int = 0
    cast_speed: int = 0
    physical_critical: int = 0
    magical_critical: int = 0
    hit_rate: int = 0
    evasion_rate: int = 0
    
    # 额外属性
    extra_stats: Dict[str, int] = field(default_factory=dict)
    
    # 价格
    price: int = 0
    sell_price: int = 0
    
    # 贸易限制
    tradeable: bool = True
    account_tradeable: bool = False
    sealable: bool = False
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "ItemRecord":
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class EquipmentItem:
    """装备物品实例"""
    instance_id: int = 0
    item_id: int = 0
    item_name: str = ""
    
    # 强化/增幅
    reinforce_level: int = 0
    amplify_level: int = 0
    amplify_type: str = ""  # strength/intelligence/vitality/spirit
    
    # 附魔
    enchant_card_id: int = 0
    enchant_name: str = ""
    
    # 徽章
    badge_slots: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    
    # 品级
    quality: int = 100  # 最上级100 ~ 最下级0
    
    # 耐久度
    durability: int = 100
    max_durability: int = 100
    
    # 封装状态
    sealed: bool = False
    
    # 获得时间
    obtain_time: float = 0.0
    
    def __post_init__(self):
        if not self.obtain_time:
            self.obtain_time = time.time()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "EquipmentItem":
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class InventorySlot:
    """背包槽位"""
    slot_index: int = 0
    item_id: int = 0
    item_name: str = ""
    item_type: str = ""
    count: int = 0
    
    # 装备实例（仅装备类型）
    equipment: Optional[EquipmentItem] = None
    
    # 过期时间（0表示永不过期）
    expire_time: float = 0.0
    
    @property
    def is_empty(self) -> bool:
        """是否为空"""
        return self.item_id == 0 or self.count <= 0
    
    def clear(self):
        """清空槽位"""
        self.item_id = 0
        self.item_name = ""
        self.item_type = ""
        self.count = 0
        self.equipment = None
        self.expire_time = 0.0


@dataclass
class Inventory:
    """背包"""
    inventory_type: int = 0
    capacity: int = 64
    slots: List[InventorySlot] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.slots:
            self.slots = [InventorySlot(slot_index=i) for i in range(self.capacity)]
    
    def get_empty_slot(self) -> Optional[InventorySlot]:
        """获取空槽位"""
        for slot in self.slots:
            if slot.is_empty:
                return slot
        return None
    
    def find_item(self, item_id: int) -> List[InventorySlot]:
        """查找物品"""
        return [slot for slot in self.slots if slot.item_id == item_id and not slot.is_empty]
    
    def add_item(
        self,
        item_id: int,
        item_name: str,
        item_type: str,
        count: int = 1,
        equipment: Optional[EquipmentItem] = None,
    ) -> Tuple[bool, int]:
        """
        添加物品
        
        Returns:
            (是否成功, 剩余未添加数量)
        """
        remaining = count
        
        # 装备类物品不能堆叠
        if item_type == ItemType.EQUIPMENT.value and equipment:
            slot = self.get_empty_slot()
            if not slot:
                return False, remaining
            slot.item_id = item_id
            slot.item_name = item_name
            slot.item_type = item_type
            slot.count = 1
            slot.equipment = equipment
            return True, 0
        
        # 可堆叠物品先尝试叠加
        existing_slots = self.find_item(item_id)
        for slot in existing_slots:
            if remaining <= 0:
                break
            # 假设最大堆叠9999
            max_stack = 9999
            can_add = max_stack - slot.count
            if can_add > 0:
                add_count = min(remaining, can_add)
                slot.count += add_count
                remaining -= add_count
        
        # 剩余的放入新槽位
        while remaining > 0:
            slot = self.get_empty_slot()
            if not slot:
                return False, remaining
            add_count = min(remaining, 9999)
            slot.item_id = item_id
            slot.item_name = item_name
            slot.item_type = item_type
            slot.count = add_count
            remaining -= add_count
        
        return True, 0
    
    def remove_item(self, item_id: int, count: int = 1) -> Tuple[bool, int]:
        """
        移除物品
        
        Returns:
            (是否成功, 实际移除数量)
        """
        remaining = count
        removed = 0
        
        slots = self.find_item(item_id)
        for slot in slots:
            if remaining <= 0:
                break
            remove_count = min(remaining, slot.count)
            slot.count -= remove_count
            remaining -= remove_count
            removed += remove_count
            if slot.is_empty:
                slot.clear()
        
        return removed == count, removed
    
    def get_item_count(self, item_id: int) -> int:
        """获取物品数量"""
        return sum(slot.count for slot in self.find_item(item_id))
    
    def move_item(self, from_slot: int, to_slot: int) -> bool:
        """移动物品"""
        if from_slot < 0 or from_slot >= self.capacity:
            return False
        if to_slot < 0 or to_slot >= self.capacity:
            return False
        
        src = self.slots[from_slot]
        dst = self.slots[to_slot]
        
        if src.is_empty:
            return False
        
        # 交换
        src.slot_index, dst.slot_index = dst.slot_index, src.slot_index
        self.slots[from_slot], self.slots[to_slot] = dst, src
        self.slots[from_slot].slot_index = from_slot
        self.slots[to_slot].slot_index = to_slot
        
        return True
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "inventory_type": self.inventory_type,
            "capacity": self.capacity,
            "slots": [
                {
                    "slot_index": slot.slot_index,
                    "item_id": slot.item_id,
                    "item_name": slot.item_name,
                    "item_type": slot.item_type,
                    "count": slot.count,
                    "equipment": slot.equipment.to_dict() if slot.equipment else None,
                    "expire_time": slot.expire_time,
                }
                for slot in self.slots
            ],
        }


@dataclass
class CharacterInventory:
    """角色背包（包含所有类型）"""
    character_id: str = ""
    
    # 各类型背包
    equipment_inventory: Inventory = field(default_factory=lambda: Inventory(inventory_type=0, capacity=64))
    consumable_inventory: Inventory = field(default_factory=lambda: Inventory(inventory_type=1, capacity=64))
    material_inventory: Inventory = field(default_factory=lambda: Inventory(inventory_type=2, capacity=64))
    quest_inventory: Inventory = field(default_factory=lambda: Inventory(inventory_type=3, capacity=32))
    profession_inventory: Inventory = field(default_factory=lambda: Inventory(inventory_type=4, capacity=32))
    
    # 快捷栏
    shortcut_inventory: Inventory = field(default_factory=lambda: Inventory(inventory_type=5, capacity=12))
    
    # 已装备
    equipped_items: Dict[int, EquipmentItem] = field(default_factory=dict)
    
    def get_inventory(self, inv_type: int) -> Optional[Inventory]:
        """获取指定类型背包"""
        inv_map = {
            InventoryType.EQUIPMENT.value: self.equipment_inventory,
            InventoryType.CONSUMABLE.value: self.consumable_inventory,
            InventoryType.MATERIAL.value: self.material_inventory,
            InventoryType.QUEST.value: self.quest_inventory,
            InventoryType.PROFESSION.value: self.profession_inventory,
            InventoryType.SHORTCUT.value: self.shortcut_inventory,
        }
        return inv_map.get(inv_type)
    
    def add_item(
        self,
        item_id: int,
        item_name: str,
        item_type: str,
        count: int = 1,
        inv_type: Optional[int] = None,
        equipment: Optional[EquipmentItem] = None,
    ) -> Tuple[bool, int]:
        """添加物品"""
        # 确定背包类型
        if inv_type is None:
            type_map = {
                ItemType.EQUIPMENT.value: InventoryType.EQUIPMENT.value,
                ItemType.CONSUMABLE.value: InventoryType.CONSUMABLE.value,
                ItemType.MATERIAL.value: InventoryType.MATERIAL.value,
                ItemType.QUEST.value: InventoryType.QUEST.value,
                ItemType.PROFESSION.value: InventoryType.PROFESSION.value,
            }
            inv_type = type_map.get(item_type, InventoryType.MATERIAL.value)
        
        inventory = self.get_inventory(inv_type)
        if not inventory:
            return False, count
        
        return inventory.add_item(item_id, item_name, item_type, count, equipment)
    
    def equip_item(self, slot_index: int, equip_slot: int) -> bool:
        """装备物品"""
        inventory = self.equipment_inventory
        if slot_index < 0 or slot_index >= inventory.capacity:
            return False
        
        slot = inventory.slots[slot_index]
        if slot.is_empty or not slot.equipment:
            return False
        
        # 检查装备部位
        # 这里简化处理，实际需要检查物品的equip_slot
        
        # 如果该部位已有装备，先卸下
        if equip_slot in self.equipped_items:
            old_equip = self.equipped_items[equip_slot]
            # 放回背包
            empty_slot = inventory.get_empty_slot()
            if empty_slot:
                empty_slot.item_id = old_equip.item_id
                empty_slot.item_name = old_equip.item_name
                empty_slot.item_type = ItemType.EQUIPMENT.value
                empty_slot.count = 1
                empty_slot.equipment = old_equip
        
        # 装备新物品
        self.equipped_items[equip_slot] = slot.equipment
        slot.clear()
        
        return True
    
    def unequip_item(self, equip_slot: int) -> bool:
        """卸下装备"""
        if equip_slot not in self.equipped_items:
            return False
        
        equip = self.equipped_items[equip_slot]
        inventory = self.equipment_inventory
        empty_slot = inventory.get_empty_slot()
        if not empty_slot:
            return False
        
        empty_slot.item_id = equip.item_id
        empty_slot.item_name = equip.item_name
        empty_slot.item_type = ItemType.EQUIPMENT.value
        empty_slot.count = 1
        empty_slot.equipment = equip
        
        del self.equipped_items[equip_slot]
        
        return True
    
    def get_total_item_count(self, item_id: int) -> int:
        """获取所有背包中物品总数"""
        total = 0
        for inv_type in InventoryType:
            inventory = self.get_inventory(inv_type.value)
            if inventory:
                total += inventory.get_item_count(item_id)
        return total
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "character_id": self.character_id,
            "equipment_inventory": self.equipment_inventory.to_dict(),
            "consumable_inventory": self.consumable_inventory.to_dict(),
            "material_inventory": self.material_inventory.to_dict(),
            "quest_inventory": self.quest_inventory.to_dict(),
            "profession_inventory": self.profession_inventory.to_dict(),
            "shortcut_inventory": self.shortcut_inventory.to_dict(),
            "equipped_items": {
                str(slot): equip.to_dict() for slot, equip in self.equipped_items.items()
            },
        }


class ItemManager:
    """物品管理器"""
    
    def __init__(self):
        # 物品模板（item_id -> ItemRecord）
        self._item_templates: Dict[int, ItemRecord] = {}
        
        # 角色背包（character_id -> CharacterInventory）
        self._inventories: Dict[str, CharacterInventory] = {}
        
        # 实例ID计数器
        self._instance_id_counter = 0
    
    def register_item_template(self, item: ItemRecord) -> None:
        """注册物品模板"""
        self._item_templates[item.item_id] = item
    
    def get_item_template(self, item_id: int) -> Optional[ItemRecord]:
        """获取物品模板"""
        return self._item_templates.get(item_id)
    
    def get_inventory(self, character_id: str) -> CharacterInventory:
        """获取角色背包"""
        if character_id not in self._inventories:
            self._inventories[character_id] = CharacterInventory(character_id=character_id)
        return self._inventories[character_id]
    
    def create_equipment_instance(
        self,
        item_id: int,
        reinforce_level: int = 0,
        amplify_level: int = 0,
        amplify_type: str = "",
    ) -> Optional[EquipmentItem]:
        """创建设备实例"""
        template = self.get_item_template(item_id)
        if not template:
            return None
        
        self._instance_id_counter += 1
        
        return EquipmentItem(
            instance_id=self._instance_id_counter,
            item_id=item_id,
            item_name=template.item_name,
            reinforce_level=reinforce_level,
            amplify_level=amplify_level,
            amplify_type=amplify_type,
        )
    
    def give_item(
        self,
        character_id: str,
        item_id: int,
        count: int = 1,
        reinforce_level: int = 0,
        amplify_level: int = 0,
    ) -> Tuple[bool, int]:
        """
        发放物品
        
        Returns:
            (是否成功, 剩余未发放数量)
        """
        template = self.get_item_template(item_id)
        if not template:
            return False, count
        
        inventory = self.get_inventory(character_id)
        
        # 装备类物品需要创建实例
        if template.item_type == ItemType.EQUIPMENT.value:
            for i in range(count):
                equip = self.create_equipment_instance(
                    item_id, reinforce_level, amplify_level
                )
                success, remaining = inventory.add_item(
                    item_id, template.item_name, template.item_type, 1, equipment=equip
                )
                if not success:
                    return False, count - i
            return True, 0
        
        # 普通物品
        return inventory.add_item(
            item_id, template.item_name, template.item_type, count
        )
