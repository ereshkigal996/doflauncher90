"""
任务系统模块
实现DNF任务数据模型、任务接受、完成、奖励、任务链等
"""

import time
import logging
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


# 日志
logger = logging.getLogger(__name__)


# 任务类型
class QuestType(Enum):
    """任务类型"""
    MAIN = "main"              # 主线任务
    SIDE = "side"              # 支线任务
    DAILY = "daily"            # 每日任务
    REPEATABLE = "repeatable"  # 重复任务
    ACHIEVEMENT = "achievement" # 成就任务
    EVENT = "event"            # 活动任务
    OTHER = "other"            # 其他


# 任务状态
class QuestStatus(Enum):
    """任务状态"""
    NOT_STARTED = 0     # 未开始
    IN_PROGRESS = 1     # 进行中
    COMPLETED = 2       # 已完成（未领取奖励）
    FINISHED = 3        # 已结束（已领取奖励）
    FAILED = 4          # 失败
    ABANDONED = 5       # 已放弃


# 任务目标类型
class QuestObjectiveType(Enum):
    """任务目标类型"""
    KILL_MONSTER = "kill_monster"        # 击杀怪物
    COLLECT_ITEM = "collect_item"        # 收集物品
    TALK_TO_NPC = "talk_to_npc"          # 与NPC对话
    REACH_LOCATION = "reach_location"    # 到达指定地点
    CLEAR_DUNGEON = "clear_dungeon"      # 通关副本
    USE_ITEM = "use_item"                # 使用物品
    EQUIP_ITEM = "equip_item"            # 装备物品
    LEVEL_UP = "level_up"                # 升级
    OTHER = "other"                      # 其他


@dataclass
class QuestObjective:
    """任务目标"""
    objective_id: int = 0
    objective_type: str = QuestObjectiveType.OTHER.value
    description: str = ""
    
    # 目标参数
    target_id: int = 0              # 目标ID（怪物ID/物品ID/NPC ID等）
    target_name: str = ""           # 目标名称
    required_count: int = 1         # 需要完成的数量
    current_count: int = 0          # 当前完成数量
    
    # 位置参数（用于到达指定地点）
    map_id: int = 0
    x: float = 0.0
    y: float = 0.0
    radius: float = 0.0
    
    # 副本参数
    dungeon_id: int = 0
    difficulty: int = 0
    
    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.current_count >= self.required_count
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)


@dataclass
class QuestReward:
    """任务奖励"""
    exp: int = 0                    # 经验值
    gold: int = 0                   # 金币
    cera: int = 0                   # 点券
    skill_points: int = 0           # 技能点
    
    # 物品奖励
    items: List[Dict[str, Any]] = field(default_factory=list)
    # 格式: [{"item_id": 1001, "item_name": "xxx", "count": 1}]
    
    # 装备奖励
    equipments: List[Dict[str, Any]] = field(default_factory=list)
    # 格式: [{"item_id": 3001, "item_name": "xxx", "reinforce_level": 0}]
    
    # 称号奖励
    title_id: int = 0
    title_name: str = ""
    
    # 其他奖励
    other_rewards: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)


@dataclass
class QuestTemplate:
    """任务模板"""
    quest_id: int = 0
    quest_name: str = ""
    quest_type: str = QuestType.SIDE.value
    description: str = ""
    detailed_description: str = ""
    
    # 等级限制
    min_level: int = 1
    max_level: int = 100
    
    # 职业限制（空列表表示不限制）
    job_required: List[str] = field(default_factory=list)
    
    # 前置任务（必须完成这些任务才能接受）
    prerequisite_quests: List[int] = field(default_factory=list)
    
    # 任务目标
    objectives: List[QuestObjective] = field(default_factory=list)
    
    # 任务奖励
    reward: QuestReward = field(default_factory=QuestReward)
    
    # NPC信息
    start_npc_id: int = 0
    start_npc_name: str = ""
    end_npc_id: int = 0
    end_npc_name: str = ""
    
    # 任务地点
    start_map_id: int = 0
    end_map_id: int = 0
    
    # 是否可放弃
    abandonable: bool = True
    
    # 是否可共享
    shareable: bool = False
    
    # 每日重置时间（仅每日任务）
    daily_reset_hour: int = 6
    
    # 任务分类
    category: str = ""
    sub_category: str = ""
    
    # 任务链信息
    chain_id: int = 0
    chain_order: int = 0
    
    def to_dict(self) -> dict:
        """转换为字典"""
        data = asdict(self)
        data['objectives'] = [obj.to_dict() for obj in self.objectives]
        data['reward'] = self.reward.to_dict()
        return data


@dataclass
class ActiveQuest:
    """已接受的任务实例"""
    quest_id: int = 0
    quest_name: str = ""
    status: int = QuestStatus.NOT_STARTED.value
    
    # 任务目标进度
    objectives: List[QuestObjective] = field(default_factory=list)
    
    # 时间信息
    accept_time: float = 0.0
    complete_time: float = 0.0
    finish_time: float = 0.0
    expire_time: float = 0.0
    
    # 任务链信息
    chain_id: int = 0
    chain_order: int = 0
    
    # 额外数据
    extra_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.accept_time:
            self.accept_time = time.time()
    
    @property
    def is_in_progress(self) -> bool:
        """是否进行中"""
        return self.status == QuestStatus.IN_PROGRESS.value
    
    @property
    def is_completed(self) -> bool:
        """是否已完成（未领取奖励）"""
        return self.status == QuestStatus.COMPLETED.value
    
    @property
    def is_finished(self) -> bool:
        """是否已结束（已领取奖励）"""
        return self.status == QuestStatus.FINISHED.value
    
    @property
    def all_objectives_completed(self) -> bool:
        """所有目标是否都已完成"""
        if not self.objectives:
            return True
        return all(obj.is_completed for obj in self.objectives)
    
    def update_objective(self, objective_id: int, count: int = 1) -> bool:
        """
        更新任务目标进度
        
        Args:
            objective_id: 目标ID
            count: 增加的数量
            
        Returns:
            是否更新成功
        """
        for obj in self.objectives:
            if obj.objective_id == objective_id:
                obj.current_count = min(obj.current_count + count, obj.required_count)
                return True
        return False
    
    def check_completion(self) -> bool:
        """检查任务是否完成，如果完成则更新状态"""
        if self.is_in_progress and self.all_objectives_completed:
            self.status = QuestStatus.COMPLETED.value
            self.complete_time = time.time()
            return True
        return False
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "quest_id": self.quest_id,
            "quest_name": self.quest_name,
            "status": self.status,
            "objectives": [obj.to_dict() for obj in self.objectives],
            "accept_time": self.accept_time,
            "complete_time": self.complete_time,
            "finish_time": self.finish_time,
            "expire_time": self.expire_time,
            "chain_id": self.chain_id,
            "chain_order": self.chain_order,
            "extra_data": self.extra_data,
        }


class QuestManager:
    """任务管理器"""
    
    def __init__(self):
        # 任务模板（quest_id -> QuestTemplate）
        self._quest_templates: Dict[int, QuestTemplate] = {}
        
        # 角色已接受任务（character_id -> {quest_id -> ActiveQuest}）
        self._active_quests: Dict[str, Dict[int, ActiveQuest]] = {}
        
        # 角色已完成任务（character_id -> {quest_id -> finish_time}）
        self._completed_quests: Dict[str, Dict[int, float]] = {}
    
    def register_quest_template(self, quest: QuestTemplate) -> None:
        """注册任务模板"""
        self._quest_templates[quest.quest_id] = quest
        logger.info(f"注册任务: {quest.quest_name} (ID={quest.quest_id})")
    
    def get_quest_template(self, quest_id: int) -> Optional[QuestTemplate]:
        """获取任务模板"""
        return self._quest_templates.get(quest_id)
    
    def get_all_quest_templates(self) -> List[QuestTemplate]:
        """获取所有任务模板"""
        return list(self._quest_templates.values())
    
    def get_available_quests(
        self,
        character_id: str,
        character_level: int = 1,
        character_job: str = "",
    ) -> List[QuestTemplate]:
        """
        获取角色可接受的任务列表
        
        Args:
            character_id: 角色ID
            character_level: 角色等级
            character_job: 角色职业
            
        Returns:
            可接受的任务列表
        """
        available = []
        completed = self._completed_quests.get(character_id, {})
        active = self._active_quests.get(character_id, {})
        
        for quest in self._quest_templates.values():
            # 已完成的任务不显示
            if quest.quest_id in completed:
                continue
            
            # 已接受的任务不显示
            if quest.quest_id in active:
                continue
            
            # 等级限制
            if character_level < quest.min_level or character_level > quest.max_level:
                continue
            
            # 职业限制
            if quest.job_required and character_job not in quest.job_required:
                continue
            
            # 前置任务检查
            prerequisites_met = all(
                pre_quest_id in completed
                for pre_quest_id in quest.prerequisite_quests
            )
            if not prerequisites_met:
                continue
            
            available.append(quest)
        
        return available
    
    def can_accept_quest(
        self,
        character_id: str,
        quest_id: int,
        character_level: int = 1,
        character_job: str = "",
    ) -> Tuple[bool, str]:
        """
        检查是否可以接受任务
        
        Returns:
            (是否可以, 原因)
        """
        template = self.get_quest_template(quest_id)
        if not template:
            return False, "任务不存在"
        
        # 已完成检查
        completed = self._completed_quests.get(character_id, {})
        if quest_id in completed:
            return False, "任务已完成"
        
        # 已接受检查
        active = self._active_quests.get(character_id, {})
        if quest_id in active:
            return False, "任务已接受"
        
        # 等级限制
        if character_level < template.min_level:
            return False, f"等级不足（需要{template.min_level}级）"
        if character_level > template.max_level:
            return False, f"等级超过限制（最高{template.max_level}级）"
        
        # 职业限制
        if template.job_required and character_job not in template.job_required:
            return False, "职业不符合"
        
        # 前置任务检查
        for pre_quest_id in template.prerequisite_quests:
            if pre_quest_id not in completed:
                pre_template = self.get_quest_template(pre_quest_id)
                pre_name = pre_template.quest_name if pre_template else f"任务{pre_quest_id}"
                return False, f"需要先完成任务：{pre_name}"
        
        return True, ""
    
    def accept_quest(
        self,
        character_id: str,
        quest_id: int,
        character_level: int = 1,
        character_job: str = "",
    ) -> Tuple[bool, str]:
        """
        接受任务
        
        Returns:
            (是否成功, 原因)
        """
        # 检查是否可以接受
        can_accept, reason = self.can_accept_quest(
            character_id, quest_id, character_level, character_job
        )
        if not can_accept:
            return False, reason
        
        template = self.get_quest_template(quest_id)
        
        # 创建任务实例
        active_quest = ActiveQuest(
            quest_id=quest_id,
            quest_name=template.quest_name,
            status=QuestStatus.IN_PROGRESS.value,
            objectives=[
                QuestObjective(
                    objective_id=obj.objective_id,
                    objective_type=obj.objective_type,
                    description=obj.description,
                    target_id=obj.target_id,
                    target_name=obj.target_name,
                    required_count=obj.required_count,
                    current_count=0,
                )
                for obj in template.objectives
            ],
            chain_id=template.chain_id,
            chain_order=template.chain_order,
        )
        
        # 保存到角色任务列表
        if character_id not in self._active_quests:
            self._active_quests[character_id] = {}
        self._active_quests[character_id][quest_id] = active_quest
        
        logger.info(f"角色{character_id}接受任务: {template.quest_name}")
        
        return True, ""
    
    def get_active_quests(self, character_id: str) -> List[ActiveQuest]:
        """获取角色进行中的任务列表"""
        active = self._active_quests.get(character_id, {})
        return [
            quest for quest in active.values()
            if quest.is_in_progress or quest.is_completed
        ]
    
    def get_active_quest(self, character_id: str, quest_id: int) -> Optional[ActiveQuest]:
        """获取角色指定的进行中任务"""
        active = self._active_quests.get(character_id, {})
        return active.get(quest_id)
    
    def update_quest_objective(
        self,
        character_id: str,
        quest_id: int,
        objective_id: int,
        count: int = 1,
    ) -> Tuple[bool, str]:
        """
        更新任务目标进度
        
        Returns:
            (是否成功, 原因)
        """
        active_quest = self.get_active_quest(character_id, quest_id)
        if not active_quest:
            return False, "任务不存在或未接受"
        
        if not active_quest.is_in_progress:
            return False, "任务已完成或已结束"
        
        # 更新目标进度
        success = active_quest.update_objective(objective_id, count)
        if not success:
            return False, "任务目标不存在"
        
        # 检查任务是否完成
        if active_quest.check_completion():
            logger.info(f"角色{character_id}完成任务: {active_quest.quest_name}")
            return True, "任务已完成，可以领取奖励"
        
        return True, ""
    
    def update_quest_by_event(
        self,
        character_id: str,
        event_type: str,
        target_id: int = 0,
        count: int = 1,
    ) -> List[Tuple[int, bool]]:
        """
        根据事件更新所有相关任务的目标进度
        
        Args:
            character_id: 角色ID
            event_type: 事件类型（击杀怪物/收集物品等）
            target_id: 目标ID
            count: 数量
            
        Returns:
            [(quest_id, 是否刚完成), ...]
        """
        results = []
        active_quests = self.get_active_quests(character_id)
        
        for quest in active_quests:
            if not quest.is_in_progress:
                continue
            
            # 查找匹配的目标
            for obj in quest.objectives:
                if obj.objective_type == event_type and obj.target_id == target_id:
                    was_completed = quest.all_objectives_completed
                    quest.update_objective(obj.objective_id, count)
                    just_completed = quest.check_completion()
                    
                    if just_completed or not was_completed:
                        results.append((quest.quest_id, just_completed))
                    break
        
        return results
    
    def complete_quest(
        self,
        character_id: str,
        quest_id: int,
    ) -> Tuple[bool, str, Optional[QuestReward]]:
        """
        完成任务并领取奖励
        
        Returns:
            (是否成功, 原因, 奖励)
        """
        active_quest = self.get_active_quest(character_id, quest_id)
        if not active_quest:
            return False, "任务不存在或未接受", None
        
        if not active_quest.is_completed:
            if active_quest.all_objectives_completed:
                active_quest.check_completion()
            else:
                return False, "任务尚未完成", None
        
        template = self.get_quest_template(quest_id)
        if not template:
            return False, "任务模板不存在", None
        
        # 更新任务状态
        active_quest.status = QuestStatus.FINISHED.value
        active_quest.finish_time = time.time()
        
        # 记录已完成任务
        if character_id not in self._completed_quests:
            self._completed_quests[character_id] = {}
        self._completed_quests[character_id][quest_id] = active_quest.finish_time
        
        # 从进行中任务移除
        if character_id in self._active_quests:
            self._active_quests[character_id].pop(quest_id, None)
        
        logger.info(f"角色{character_id}完成任务并领取奖励: {template.quest_name}")
        
        return True, "任务完成", template.reward
    
    def abandon_quest(
        self,
        character_id: str,
        quest_id: int,
    ) -> Tuple[bool, str]:
        """
        放弃任务
        
        Returns:
            (是否成功, 原因)
        """
        active_quest = self.get_active_quest(character_id, quest_id)
        if not active_quest:
            return False, "任务不存在或未接受"
        
        template = self.get_quest_template(quest_id)
        if template and not template.abandonable:
            return False, "该任务不可放弃"
        
        # 从进行中任务移除
        if character_id in self._active_quests:
            self._active_quests[character_id].pop(quest_id, None)
        
        logger.info(f"角色{character_id}放弃任务: {active_quest.quest_name}")
        
        return True, ""
    
    def get_completed_quests(self, character_id: str) -> Dict[int, float]:
        """获取角色已完成的任务列表"""
        return self._completed_quests.get(character_id, {})
    
    def has_completed_quest(self, character_id: str, quest_id: int) -> bool:
        """检查角色是否已完成指定任务"""
        completed = self._completed_quests.get(character_id, {})
        return quest_id in completed
    
    def get_quest_progress_summary(self, character_id: str) -> Dict[str, Any]:
        """获取角色任务进度摘要"""
        active = self.get_active_quests(character_id)
        completed = self.get_completed_quests(character_id)
        
        in_progress = [q for q in active if q.is_in_progress]
        can_claim = [q for q in active if q.is_completed]
        
        return {
            "in_progress_count": len(in_progress),
            "can_claim_count": len(can_claim),
            "completed_count": len(completed),
            "in_progress_quests": [q.to_dict() for q in in_progress],
            "can_claim_quests": [q.to_dict() for q in can_claim],
        }
    
    def reset_daily_quests(self, character_id: str) -> int:
        """
        重置每日任务
        
        Returns:
            重置的任务数量
        """
        # 这里可以实现每日任务重置逻辑
        # 暂时返回0
        return 0
    
    def to_dict(self, character_id: str) -> dict:
        """转换为字典"""
        return {
            "character_id": character_id,
            "active_quests": [
                quest.to_dict()
                for quest in self.get_active_quests(character_id)
            ],
            "completed_quests": {
                str(quest_id): finish_time
                for quest_id, finish_time in self.get_completed_quests(character_id).items()
            },
            "progress_summary": self.get_quest_progress_summary(character_id),
        }
